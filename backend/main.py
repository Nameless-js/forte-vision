import asyncio
import base64
import hmac
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4, UUID
from datetime import datetime, timezone

import httpx
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, Query
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from .storage import create_repository
from fastapi.staticfiles import StaticFiles
from .model_adapter import analyze_video
from .media_routes import media_router
from .checks import validate_checks

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env', override=False)
DATA = Path(os.getenv('DATA_DIRECTORY', str(ROOT / 'runtime')))
DATA.mkdir(parents=True, exist_ok=True)
KEY = os.getenv('API_KEY')
if not KEY:
    key_path = DATA / '.api-key'
    if not key_path.exists():
        key_path.write_text(secrets.token_urlsafe(32), encoding='utf-8')
    KEY = key_path.read_text(encoding='utf-8').strip()
MAX_BYTES = 100 * 1024 * 1024
repository = create_repository(DATA)
tasks: set[asyncio.Task] = set()

def validate_result(value):
    if value.get('verdict') not in ('violation','no_violation'):
        raise ValueError('Модель вернула неподдерживаемый verdict')
    events = value.get('violations')
    if not isinstance(events, list) or (bool(events) != (value['verdict']=='violation')):
        raise ValueError('verdict и violations не согласованы')
    for event in events:
        if not isinstance(event.get('type'),str) or not event['type'].strip() or not isinstance(event.get('description'),str) or not event['description'].strip():
            raise ValueError('Событию нужны type и description')
        validate_checks(event.get('checks', []))
        timestamp = event.get('timecode_sec')
        if not isinstance(timestamp,(int,float)) or not 0 <= timestamp < float('inf'):
            raise ValueError('Некорректный таймкод')
        frames = event.get('evidence_frames')
        if not isinstance(frames,list) or not 1 <= len(frames) <= 3:
            raise ValueError('Для события нужны 1–3 кадра')
        for frame in frames:
            ts = frame.get('timestamp_sec')
            if not isinstance(ts,(int,float)) or not 0 <= ts < float('inf'):
                raise ValueError('Некорректное время кадра')
            image = base64.b64decode(frame.get('image_base64',''),validate=True)
            if not image.startswith(b'\xff\xd8\xff'):
                raise ValueError('Кадр должен быть JPEG в base64')
    return value

async def process(job_id, path, metadata):
    start = time.monotonic()
    try:
        value = await asyncio.wait_for(asyncio.to_thread(analyze_video,path), timeout=270)
        validated = validate_result(value)
        payload = {**validated, **metadata, 'job_id':job_id,'status':'done','processing_seconds':round(time.monotonic()-start,2)}
    except asyncio.TimeoutError:
        payload = {**metadata,'job_id':job_id,'status':'failed','violations':[],'error':'Модель превысила лимит 270 секунд'}
    except Exception as exc:
        payload = {**metadata,'job_id':job_id,'status':'failed','violations':[],'error':str(exc)[:500]}
    finally:
        path.unlink(missing_ok=True)
    await repository.save(payload)

@asynccontextmanager
async def lifespan(app):
    await repository.check()
    for payload in await repository.list(1000):
        if payload['status']=='processing':
            await repository.save({**payload,'status':'failed','violations':[],'error':'Сервер перезапущен. Загрузите видео повторно.'})
    yield
    for task in list(tasks):
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks,return_exceptions=True)

app = FastAPI(title='BlockWatch API', version='0.1.0', lifespan=lifespan)

async def authorize(x_api_key: str = Header(default='')):
    if not hmac.compare_digest(x_api_key, KEY):
        raise HTTPException(401,'Неверный X-API-Key')

@app.get('/api/health')
async def health():
    try:
        await repository.check()
    except httpx.HTTPError:
        raise HTTPException(503,'База данных недоступна')
    return {'status':'ok','model':'adapter','storage':repository.name,'database_connected':True}

@app.post('/api/v1/analyze', dependencies=[Depends(authorize)],status_code=202)
async def analyze(file: UploadFile = File(...)):
    if Path(file.filename or '').suffix.lower() not in ('.mov','.mp4','.webm'):
        raise HTTPException(415,'Поддерживаются MOV, MP4 и WebM')
    if sum(not t.done() for t in tasks) >= 2:
        raise HTTPException(429,'Сервер занят, повторите запрос позже')
    job_id = str(uuid4())
    path = DATA / f'{job_id}{Path(file.filename).suffix.lower()}'
    size = 0
    try:
        with path.open('wb') as output:
            while chunk := await file.read(1024*1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413,'Максимальный размер 100 МБ')
                output.write(chunk)
        if size == 0:
            raise HTTPException(400,'Пустой файл')
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    metadata={'filename':Path(file.filename or 'video').name[:255],'file_size':size,'created_at':datetime.now(timezone.utc).isoformat()}
    try:
        await repository.save({**metadata,'job_id':job_id,'status':'processing','violations':[]})
    except httpx.HTTPError:
        path.unlink(missing_ok=True)
        raise HTTPException(503,'Не удалось сохранить проверку в базе')
    task = asyncio.create_task(process(job_id,path,metadata))
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return {'job_id':job_id}

@app.get('/api/v1/jobs/{job_id}', dependencies=[Depends(authorize)])
async def job(job_id: str):
    try:
        UUID(job_id)
    except ValueError:
        raise HTTPException(404,'Задание не найдено')
    payload = await repository.get(job_id)
    if payload is None:
        raise HTTPException(404,'Задание не найдено')
    return payload

class DemoRequest(BaseModel):
    filename: str = Field(min_length=1,max_length=255)
    file_size: int = Field(ge=0,le=MAX_BYTES)
    duration_sec: float = Field(gt=0,le=86400)

@app.post('/api/v1/demo/jobs',dependencies=[Depends(authorize)],status_code=201)
async def demo_job(data: DemoRequest):
    events=[
        {'type':'Открытое хранилище наличных','timecode_sec':min(12,data.duration_sec*.35),
         'description':'Учебный пример открытого хранилища. Это не результат анализа вашего видео.','evidence_frames':[]},
        {'type':'Передача ценностей','timecode_sec':min(28,data.duration_sec*.72),
         'description':'Учебный пример передачи ценностей. Нормативный вывод не выполнялся.','evidence_frames':[]}
    ]
    payload={'job_id':str(uuid4()),'status':'done','verdict':'violation','violations':events,'demo':True,
             **data.model_dump(),'created_at':datetime.now(timezone.utc).isoformat()}
    await repository.save(payload)
    return payload

@app.get('/api/v1/jobs',dependencies=[Depends(authorize)])
async def list_jobs(limit: int = Query(default=30,ge=1,le=100)):
    return {'jobs':[{k:v for k,v in row.items() if k not in ('violations',)} |
                    {'event_count':len(row.get('violations',[]))} for row in await repository.list(limit)]}

app.include_router(media_router(authorize, DATA, MAX_BYTES))

if (ROOT / 'dist').exists():
    app.mount('/', StaticFiles(directory=ROOT/'dist',html=True),name='frontend')
