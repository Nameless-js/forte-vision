import base64
from fastapi.testclient import TestClient
from .main import app, KEY, validate_result
import pytest
from . import main
from .storage import SQLiteJobs

@pytest.fixture(autouse=True)
def isolated_database(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'repository',SQLiteJobs(tmp_path/'jobs.sqlite'))

def test_auth_and_unknown_job():
    with TestClient(app) as client:
        assert client.get('/api/v1/jobs/missing').status_code == 401
        assert client.get('/api/v1/jobs/missing',headers={'X-API-Key':KEY}).status_code == 404

def test_upload_and_failed_model(monkeypatch):
    def invalid_video(path):
        raise ValueError('Тестовый файл не является видео')
    monkeypatch.setattr(main, 'analyze_video', invalid_video)
    with TestClient(app) as client:
        headers={'X-API-Key':KEY}
        assert client.post('/api/v1/analyze',headers=headers,files={'file':('x.txt',b'abc')}).status_code == 415
        assert client.post('/api/v1/analyze',headers=headers,files={'file':('x.mov',b'')}).status_code == 400
        r=client.post('/api/v1/analyze',headers=headers,files={'file':('x.mov',b'local-test-video')})
        assert r.status_code==202
        import time
        for _ in range(40):
            result=client.get('/api/v1/jobs/'+r.json()['job_id'],headers=headers).json()
            if result['status']!='processing':break
            time.sleep(.05)
        assert result['status']=='failed'
        assert 'не является видео' in result['error']


def test_model_contract():
    assert validate_result({'verdict':'no_violation','violations':[]})['verdict']=='no_violation'
    with pytest.raises(ValueError):validate_result({'verdict':'violation','violations':[]})
    with pytest.raises(ValueError):validate_result({'verdict':'no_violation','violations':[{}]})
    event={'type':'test','description':'observed action','timecode_sec':1,'evidence_frames':[{'timestamp_sec':1,'image_base64':base64.b64encode(b'\xff\xd8\xffexample').decode()}]}
    assert validate_result({'verdict':'violation','violations':[event]})['violations'][0]['timecode_sec']==1
    event['timecode_sec']=float('nan')
    with pytest.raises(ValueError):validate_result({'verdict':'violation','violations':[event]})

def test_saved_demo_history():
    headers={'X-API-Key':KEY}
    with TestClient(app) as client:
        result=client.post('/api/v1/demo/jobs',headers=headers,json={'filename':'synthetic.mov','file_size':123,'duration_sec':20})
        assert result.status_code==201
        saved=result.json()
        assert saved['demo'] is True
        assert len(saved['violations'])==2
        assert client.get('/api/v1/jobs/'+saved['job_id'],headers=headers).json()==saved
        history=client.get('/api/v1/jobs',headers=headers).json()['jobs']
        assert history[0]['filename']=='synthetic.mov'
        assert history[0]['event_count']==2
        assert 'violations' not in history[0]
        assert client.get('/api/health').json()['database_connected'] is True


def test_live_progress_and_single_gpu_slot(monkeypatch):
    import threading
    import time
    from .model_adapter import analysis_progress
    release = threading.Event()
    def model(path):
        callback = analysis_progress.get()
        callback(.4, 'Поиск событий')
        release.wait(timeout=5)
        return {'verdict':'no_violation','violations':[]}
    monkeypatch.setattr(main, 'analyze_video', model)
    headers = {'X-API-Key':KEY}
    with TestClient(app) as client:
        try:
            response = client.post('/api/v1/analyze',headers=headers,files={'file':('x.mov',b'fixture')})
            job_id = response.json()['job_id']
            for _ in range(40):
                data = client.get('/api/v1/jobs/'+job_id,headers=headers).json()
                if data.get('progress') == .4:
                    break
                time.sleep(.025)
            assert data['status'] == 'processing' and data['progress'] == .4
            assert data['stage'] == 'Поиск событий'
            busy = client.post('/api/v1/analyze',headers=headers,files={'file':('second.mov',b'fixture')})
            assert busy.status_code == 429
        finally:
            release.set()
