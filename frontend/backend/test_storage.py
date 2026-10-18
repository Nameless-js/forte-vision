import asyncio
import json
from uuid import uuid4
import httpx
from .storage import SupabaseJobs, SQLiteJobs

def test_supabase_writes_and_reads_same_job():
    job_id=str(uuid4())
    record={'job_id':job_id,'status':'done','demo':True,'filename':'example.mov','violations':[]}
    stored={}
    def handler(request):
        assert request.headers['apikey']=='sb_secret_test'
        assert 'authorization' not in request.headers
        if request.method=='POST':
            value=json.loads(request.content)
            assert value['mode']=='demo'
            assert value['id']==job_id
            stored.update(value)
            return httpx.Response(201)
        if request.url.params.get('select')=='id':return httpx.Response(200,json=[])
        return httpx.Response(200,json=[{'result':stored['result']}])
    async def run():
        repo=SupabaseJobs('http://127.0.0.1:54321','sb_secret_test',transport=httpx.MockTransport(handler))
        await repo.check()
        await repo.save(record)
        assert await repo.get(job_id)==record
        assert await repo.list()==[record]
        await repo.client.aclose()
    asyncio.run(run())

def test_sqlite_survives_repository_reopen(tmp_path):
    async def run():
        record={'job_id':str(uuid4()),'status':'done','violations':[]}
        await SQLiteJobs(tmp_path/'data.sqlite').save(record)
        assert await SQLiteJobs(tmp_path/'data.sqlite').get(record['job_id'])==record
    asyncio.run(run())
