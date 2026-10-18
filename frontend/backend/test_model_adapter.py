from pathlib import Path
import pytest
from . import model_adapter as adapter

@pytest.fixture(autouse=True)
def clean_adapter(monkeypatch):
    monkeypatch.setattr(adapter, '_engine', None)
    adapter._cancel.clear()
    yield
    adapter.close_analyzer()


def test_engine_evidence_and_citations_survive_adaptation(monkeypatch):
    source = {'verdict':'violation', 'violations':[{'type':'Нарушение', 'description':'Видимое действие',
        'timecode_sec':12.4, 'evidence_frames':[{'timestamp_sec':12.4, 'image_base64':'/9j/'}],
        'rule':{'document':'Акт РК', 'clause':'п. 12', 'url':'https://adilet.zan.kz/rus/docs/test'}}],
        'video':{'duration_s':25.9}, 'engine_version':'test'}
    calls = []
    class Engine:
        def __init__(self, **kwargs):
            assert kwargs['hard_timeout_s'] < 270
        def analyze(self, path, **kwargs):
            calls.append((path,kwargs))
            return source
        def close(self):
            pass
    monkeypatch.setattr(adapter,'SupervisedAnalyzer',Engine)
    result = adapter.analyze_video(Path('input.mov'))
    assert result['duration_sec'] == 25.9
    assert result['violations'][0]['evidence_frames'] == source['violations'][0]['evidence_frames']
    assert result['violations'][0]['rule']['title'] == 'Акт РК'
    assert result['violations'][0]['rule']['section'] == 'п. 12'
    assert 'title' not in source['violations'][0]['rule']
    adapter.analyze_video(Path('second.mov'))
    assert len(calls) == 2
    assert calls[0][1]['cancel_event'] is adapter._cancel


def test_no_violation_and_engine_failure_are_not_fabricated(monkeypatch):
    class Engine:
        def __init__(self, **kwargs):
            pass
        def analyze(self, path, **kwargs):
            if path.name == 'bad.mov':
                raise TimeoutError('timed out')
            return {'verdict':'no_violation','violations':[]}
        def close(self):
            pass
    monkeypatch.setattr(adapter,'SupervisedAnalyzer',Engine)
    assert adapter.analyze_video(Path('good.mov'))['violations'] == []
    with pytest.raises(TimeoutError):
        adapter.analyze_video(Path('bad.mov'))
