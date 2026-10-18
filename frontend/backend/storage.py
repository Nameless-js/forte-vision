"""Server-only job persistence. Supabase is primary when configured."""
import asyncio
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import httpx


def normalize_id(value: str) -> str:
    return str(UUID(value))


class SQLiteJobs:
    name = 'sqlite'

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.execute('create table if not exists jobs (id text primary key, payload text not null)')
        return con

    async def check(self):
        with self._connect() as con:
            con.execute('select 1')

    async def save(self, payload):
        with self._connect() as con:
            con.execute('insert or replace into jobs values (?,?)', (payload['job_id'], json.dumps(payload, ensure_ascii=False)))

    async def get(self, job_id):
        with self._connect() as con:
            row = con.execute('select payload from jobs where id=?', (job_id,)).fetchone()
        return json.loads(row[0]) if row else None

    async def list(self, limit=30):
        with self._connect() as con:
            rows = con.execute('select payload from jobs order by rowid desc limit ?', (limit,)).fetchall()
        return [json.loads(row[0]) for row in rows]


class SupabaseJobs:
    name = 'supabase'

    def __init__(self, url, key, transport=None):
        if not url or not key:
            raise RuntimeError('Для Supabase нужны SUPABASE_URL и SUPABASE_SECRET_KEY')
        self.client = httpx.AsyncClient(base_url=url.rstrip('/')+'/rest/v1/', timeout=12, transport=transport,
                                       headers={'apikey':key, **({'Authorization':'Bearer '+key} if key.startswith('eyJ') else {})})

    async def _request(self, method, path, **kwargs):
        # GETs and idempotent upserts may safely retry transient local startup failures.
        for attempt in range(3):
            try:
                response = await self.client.request(method, path, **kwargs)
                if response.status_code >= 500 and attempt < 2:
                    await asyncio.sleep(.3 * (attempt+1))
                    continue
                response.raise_for_status()
                return response
            except httpx.TransportError:
                if attempt == 2:
                    raise
                await asyncio.sleep(.3 * (attempt+1))

    async def check(self):
        await self._request('GET','analysis_jobs',params={'select':'id','limit':'1'})

    async def save(self, payload):
        await self._request('POST','analysis_jobs',params={'on_conflict':'id'},
            headers={'Prefer':'resolution=merge-duplicates'},
            json={'id':normalize_id(payload['job_id']),'status':payload['status'],
                  'mode':'demo' if payload.get('demo') else 'model',
                  'filename':payload.get('filename'), 'file_size':payload.get('file_size'),
                  'duration_sec':payload.get('duration_sec'),
                  'result':payload,'updated_at':datetime.now(timezone.utc).isoformat()})

    async def get(self, job_id):
        response = await self._request('GET','analysis_jobs',params={'id':'eq.'+normalize_id(job_id),'select':'result','limit':'1'})
        rows = response.json()
        return rows[0]['result'] if rows else None

    async def list(self, limit=30):
        response = await self._request('GET','analysis_jobs',params={'select':'result','order':'created_at.desc','limit':str(limit)})
        return [row['result'] for row in response.json()]


def create_repository(directory):
    backend = os.getenv('DATABASE_BACKEND','sqlite')
    if backend == 'supabase':
        return SupabaseJobs(os.getenv('SUPABASE_URL'),os.getenv('SUPABASE_SECRET_KEY'))
    if backend != 'sqlite':
        raise RuntimeError('DATABASE_BACKEND должен быть sqlite или supabase')
    return SQLiteJobs(directory/'jobs.sqlite')
