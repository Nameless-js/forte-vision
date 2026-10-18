import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from .checks import validate_checks
from .media import context_frames, probe, render_video, run_ffmpeg
from . import main
from .storage import SQLiteJobs


@pytest.fixture(scope='module')
def video(tmp_path_factory):
    path = tmp_path_factory.mktemp('synthetic')/'test.mov'
    result = run_ffmpeg(['-loglevel', 'error', '-y', '-f', 'lavfi', '-i',
        'testsrc2=size=320x180:rate=10:duration=4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)])
    assert result.returncode == 0
    return path


def test_context_and_boundaries(video):
    result = context_frames(video, 2, 1)
    assert [frame['role'] for frame in result['frames']] == ['before','moment','after']
    assert [frame['timestamp_sec'] for frame in result['frames']] == [1,2,3]
    assert all(base64.b64decode(frame['image_base64']).startswith(b'\xff\xd8\xff') for frame in result['frames'])
    assert context_frames(video, 0, 3)['frames'][0]['timestamp_sec'] == 0
    assert context_frames(video, 3.9, 3)['frames'][-1]['timestamp_sec'] < 4
    with pytest.raises(ValueError):
        context_frames(video, 20, 3)


@pytest.mark.parametrize('kind',['dark','blur','occlusion'])
def test_variants_preserve_timeline(video, tmp_path, kind):
    path = render_video(video, tmp_path/'variant.mp4', kind)
    assert abs(probe(path)-probe(video)) < .15
    before = context_frames(video, 2, 1)['frames'][1]['image_base64']
    after = context_frames(path, 2, 1)['frames'][1]['image_base64']
    assert before != after


def test_clip_duration_and_bad_media(video, tmp_path):
    output = render_video(video,tmp_path/'clip.mp4',timestamp=2,window=1)
    assert abs(probe(output)-2) < .15
    bad = tmp_path/'invalid.mov'
    bad.write_bytes(b'not a video')
    with pytest.raises(ValueError):
        probe(bad)
    with pytest.raises(ValueError):
        render_video(video,tmp_path/'bad.mp4','shell;command')


def test_checks_are_explicit_and_validated():
    validate_checks([])
    validate_checks([{'id':'subject_visible','status':'unknown'}])
    check = {'id':'alternative_explanation','status':'confirmed','note':'A second visible action explains the movement','timestamp_sec':2}
    validate_checks([check])
    for checks in [[check,check],[{**check,'status':'probably'}],[{**check,'note':''}],[{**check,'timestamp_sec':float('nan')}],[{**check,'id':'invented'}]]:
        with pytest.raises(ValueError):
            validate_checks(checks)


def test_authenticated_media_routes_and_cleanup(video,tmp_path,monkeypatch):
    monkeypatch.setattr(main,'repository',SQLiteJobs(tmp_path/'jobs.sqlite'))
    headers={'X-API-Key':main.KEY}
    with TestClient(main.app) as client:
        assert client.post('/api/v1/media/context').status_code == 401
        info=client.post('/api/v1/media/info',headers=headers,files={'file':('test.mov',video.read_bytes())})
        assert info.status_code==200 and info.json()['duration_sec']==4
        assert client.post('/api/v1/media/context',headers=headers,files={'file':('bad.mov',b'x')},data={'timestamp':'2'}).status_code == 422
        result=client.post('/api/v1/media/context',headers=headers,files={'file':('test.mov',video.read_bytes())},data={'timestamp':'2','window':'1'})
        assert result.status_code==200
        assert len(result.json()['frames'])==3
        assert client.post('/api/v1/media/context',headers=headers,files={'file':('test.mov',video.read_bytes())},data={'timestamp':'nan'}).status_code == 422
        result=client.post('/api/v1/media/clip',headers=headers,files={'file':('test.mov',video.read_bytes())},data={'timestamp':'2','window':'1'})
        assert result.status_code==200 and result.headers['content-type']=='video/mp4'
        assert b'ftyp' in result.content[:40]
        result=client.post('/api/v1/media/variant',headers=headers,files={'file':('test.mov',video.read_bytes())},data={'kind':'dark'})
        assert result.status_code==200
    assert not list(main.DATA.glob('context-*'))
    assert not list(main.DATA.glob('variant-*'))


def test_model_checks_round_trip(video,tmp_path,monkeypatch):
    import time
    frame=context_frames(video,2,1)['frames'][1]
    event={'type':'Synthetic movement','description':'Test geometry changes','timecode_sec':2,
           'evidence_frames':[{'timestamp_sec':frame['timestamp_sec'],'image_base64':frame['image_base64']}],
           'checks':[{'id':'alternative_explanation','status':'confirmed','note':'Synthetic test fixture','timestamp_sec':2}]}
    monkeypatch.setattr(main,'repository',SQLiteJobs(tmp_path/'checks.sqlite'))
    monkeypatch.setattr(main,'analyze_video',lambda path:{'verdict':'violation','violations':[event]})
    headers={'X-API-Key':main.KEY}
    with TestClient(main.app) as client:
        response=client.post('/api/v1/analyze',headers=headers,files={'file':('synthetic.mov',video.read_bytes())})
        assert response.status_code==202
        job_id=response.json()['job_id']
        for _ in range(40):
            saved=client.get('/api/v1/jobs/'+job_id,headers=headers).json()
            if saved['status']!='processing':
                break
            time.sleep(.05)
        assert saved['status']=='done'
        assert saved['violations'][0]['checks']==event['checks']
