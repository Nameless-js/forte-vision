import asyncio
import base64
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from .model_adapter import analyze_video

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv('DATA_DIRECTORY', str(ROOT / 'runtime')))
DATA.mkdir(parents=True, exist_ok=True)
KEY = os.getenv('API_KEY')
if not KEY:
    key_path = DATA / '.api-key'
    if not key_path.exists():
        key_path.write_text(secrets.token_urlsafe(32), encoding='utf-8')
    KEY = key_path.read_text(encoding='utf-8').strip()
MAX_BYTES = 100 * 1024 * 1024
DB = DATA / 'jobs.sqlite'
tasks: set[asyncio.Task] = set()

def connection():
    con = sqlite3.connect(DB)
    con.execute('create table if not exists jobs (id text primary key, payload text not null)')
    return con

def store(payload):
    with connection() as con:
        con.execute('insert or replace into jobs values (?,?)', (payload['job_id'], json.dumps(payload, ensure_ascii=False)))

def read_job(job_id):
    with connection() as con:
        row = con.execute('select payload from jobs where id=?', (job_id,)).fetchone()
    return json.loads(row[0]) if row else None

async def mirror(payload):
    # Optional local Supabase REST persistence. Uploaded video stays on disk.
    url = os.getenv('SUPABASE_URL', '').rstrip('/')
    key = os.getenv('SUPABASE_SECRET_KEY', '')
    if not url or not key:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(f'{url}/rest/v1/analysis_jobs?on_conflict=id', headers={'apikey':key, 'Authorization':f'Bearer {key}', 'Prefer':'resolution=merge-duplicates'}, json={'id':payload['job_id'],'status':payload['status'],'result':payload})
            response.raise_for_status()
    except httpx.HTTPError:
        # SQLite remains authoritative; a mirror outage must not lose the job.
        import logging
        logging.getLogger('blockwatch').warning('Supabase mirror unavailable; result retained locally')

def validate_result(value):
    if value.get('verdict') not in ('violation','no_violation'):
        raise ValueError('Модель вернула неподдерживаемый verdict')
    events = value.get('violations')
    if not isinstance(events, list) or (bool(events) != (value['verdict']=='violation')):
        raise ValueError('verdict и violations не согласованы')
    for event in events:
        if not isinstance(event.get('type'),str) or not event['type'].strip() or not isinstance(event.get('description'),str) or not event['description'].strip():
            raise ValueError('Событию нужны type и description')
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

async def process(job_id, path):
    start = time.monotonic()
    payload = {'job_id':job_id,'status':'processing','violations':[]}
    await mirror(payload)
    try:
        value = await asyncio.wait_for(asyncio.to_thread(analyze_video,path), timeout=270)
        validated = validate_result(value)
        payload = {**validated,'job_id':job_id,'status':'done','processing_seconds':round(time.monotonic()-start,2)}
    except asyncio.TimeoutError:
        payload = {'job_id':job_id,'status':'failed','violations':[],'error':'Модель превысила лимит 270 секунд'}
    except Exception as exc:
        payload = {'job_id':job_id,'status':'failed','violations':[],'error':str(exc)[:500]}
    finally:
        path.unlink(missing_ok=True)
    store(payload)
    await mirror(payload)

@asynccontextmanager
async def lifespan(app):
    # Jobs interrupted by a server restart must not remain processing forever.
    with connection() as con:
        pending = [json.loads(r[0]) for r in con.execute('select payload from jobs')]
    for payload in pending:
        if payload['status']=='processing':
            store({'job_id':payload['job_id'],'status':'failed','violations':[],'error':'Сервер перезапущен. Загрузите видео повторно.'})
    yield
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks,return_exceptions=True)

app = FastAPI(title='BlockWatch API', version='0.1.0', lifespan=lifespan)

async def authorize(x_api_key: str = Header(default='')):
    if not hmac.compare_digest(x_api_key, KEY):
        raise HTTPException(401,'Неверный X-API-Key')

@app.get('/api/health')
async def health():
    return {'status':'ok','model':'adapter','storage':'sqlite','supabase_configured':bool(os.getenv('SUPABASE_URL'))}

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
    store({'job_id':job_id,'status':'processing','violations':[]})
    task = asyncio.create_task(process(job_id,path))
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return {'job_id':job_id}

@app.get('/api/v1/jobs/{job_id}', dependencies=[Depends(authorize)])
async def job(job_id: str):
    payload = read_job(job_id)
    if payload is None:
        raise HTTPException(404,'Задание не найдено')
    return payload

if (ROOT / 'dist').exists():
    app.mount('/', StaticFiles(directory=ROOT/'dist',html=True),name='frontend')
