import asyncio
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from .media import context_frames, render_video, probe


def media_router(authorize, data_directory, max_bytes):
    router = APIRouter(prefix='/api/v1/media', dependencies=[Depends(authorize)])
    slots = asyncio.Semaphore(2)

    async def upload(file, directory):
        suffix = Path(file.filename or '').suffix.lower()
        if suffix not in ('.mov', '.mp4', '.webm'):
            await file.close()
            raise HTTPException(415, 'invalid_format')
        path = Path(directory)/('input'+suffix)
        size = 0
        try:
            with path.open('wb') as target:
                while chunk := await file.read(1024*1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise HTTPException(413, 'media_size')
                    target.write(chunk)
        finally:
            await file.close()
        if not size:
            raise HTTPException(400, 'invalid_video')
        return path

    async def available():
        if slots.locked():
            raise HTTPException(429, 'media_busy')

    @router.post('/info', dependencies=[Depends(available)])
    async def info(file: UploadFile = File(...)):
        async with slots:
            with tempfile.TemporaryDirectory(prefix='context-', dir=data_directory) as directory:
                path = await upload(file, directory)
                try:
                    return {'duration_sec': await asyncio.to_thread(probe, path)}
                except ValueError as exc:
                    raise HTTPException(422, str(exc)) from exc

    @router.post('/context', dependencies=[Depends(available)])
    async def context(file: UploadFile = File(...), timestamp: float = Form(ge=0, le=600),
                      window: float = Form(default=3, ge=.5, le=10)):
        async with slots:
            with tempfile.TemporaryDirectory(prefix='context-', dir=data_directory) as directory:
                path = await upload(file, directory)
                try:
                    return await asyncio.to_thread(context_frames, path, timestamp, window)
                except ValueError as exc:
                    raise HTTPException(422, str(exc)) from exc

    async def render(file, kind, timestamp=None, window=3):
        directory = tempfile.TemporaryDirectory(prefix='variant-', dir=data_directory)
        try:
            async with slots:
                path = await upload(file, directory.name)
                output = Path(directory.name)/'video.mp4'
                await asyncio.to_thread(render_video, path, output, kind, timestamp, window)
            return FileResponse(output, media_type='video/mp4', filename='video.mp4',
                                background=BackgroundTask(directory.cleanup))
        except ValueError as exc:
            directory.cleanup()
            raise HTTPException(422, str(exc)) from exc
        except BaseException:
            directory.cleanup()
            raise

    @router.post('/clip', dependencies=[Depends(available)])
    async def clip(file: UploadFile = File(...), timestamp: float = Form(ge=0, le=600),
                   window: float = Form(default=3, ge=.5, le=10)):
        return await render(file, 'original', timestamp, window)

    @router.post('/variant', dependencies=[Depends(available)])
    async def variant(file: UploadFile = File(...),
                      kind: Literal['original', 'dark', 'blur', 'occlusion'] = Form(...)):
        return await render(file, kind)

    return router
