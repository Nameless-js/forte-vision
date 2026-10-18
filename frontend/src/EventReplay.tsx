import {Select} from './components/ui/accordion-2';
import {LocalVideo} from './LocalVideo';
import {useEffect,useRef,useState} from 'react';
import {Film,Loader2,Play,ZoomIn,X} from 'lucide-react';
import {useI18n} from './i18n';
import {clock,mediaError,safeError,type Evidence} from './analysis';
type ContextFrame=Evidence&{role:'before'|'moment'|'after'};

export function EventReplay({file,timestamp,apiKey,demo,onJump}:{file:File|null;timestamp:number;apiKey:string;demo:boolean;onJump:(time:number)=>void}){
 const {t}=useI18n();const [window,setWindow]=useState(3);const [frames,setFrames]=useState<ContextFrame[]>([]);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [zoom,setZoom]=useState<ContextFrame|null>(null);const [clip,setClip]=useState('');const [clipBusy,setClipBusy]=useState(false);const [clipError,setClipError]=useState('');const clipRequest=useRef<AbortController|null>(null);const identity=useRef(0);
 useEffect(()=>{const id=++identity.current;const controller=new AbortController();setFrames([]);setError('');setClip('');setClipError('');setClipBusy(false);clipRequest.current?.abort();if(!file)return;setBusy(true);
  const body=new FormData();body.append('file',file);body.append('timestamp',String(timestamp));body.append('window',String(window));
  fetch('/api/v1/media/context',{method:'POST',headers:{'X-API-Key':apiKey},body,signal:controller.signal}).then(async response=>{if(!response.ok)throw Error(mediaError(response.status));return response.json()}).then(data=>{if(id===identity.current)setFrames(data.frames)}).catch(e=>{if(!controller.signal.aborted&&id===identity.current)setError(safeError(e))}).finally(()=>{if(id===identity.current)setBusy(false)});
  return()=>{controller.abort();clipRequest.current?.abort()};
 },[file,timestamp,window,apiKey]);
 useEffect(()=>()=>{if(clip)URL.revokeObjectURL(clip)},[clip]);
 useEffect(()=>{if(!zoom)return;const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')setZoom(null)};document.addEventListener('keydown',escape);return()=>document.removeEventListener('keydown',escape)},[zoom]);
 async function playClip(){if(!file)return;const id=identity.current;const controller=new AbortController();clipRequest.current=controller;setClipBusy(true);setClipError('');const body=new FormData();body.append('file',file);body.append('timestamp',String(timestamp));body.append('window',String(window));try{const response=await fetch('/api/v1/media/clip',{method:'POST',headers:{'X-API-Key':apiKey},body,signal:controller.signal});if(!response.ok)throw Error(mediaError(response.status));const blob=await response.blob();if(id===identity.current)setClip(URL.createObjectURL(blob))}catch(e){if(!controller.signal.aborted)setClipError(safeError(e))}finally{if(id===identity.current)setClipBusy(false)}}
 return <section className="event-replay" aria-label={t('Восстановление события')}>
  <div className="feature-section-title"><span><Film size={17}/>{t('Восстановить событие')}</span><Select aria-label={t('Контекст в секундах')} value={window} onChange={e=>setWindow(Number(e.target.value))}>{[1,3,5].map(n=><option key={n} value={n}>±{n} {t('сек')}</option>)}</Select></div>
  <p className="feature-help">{t(demo?'Кадры настоящие, отметка события учебная. Это не результат распознавания.':'Контекст из исходного видео. Выбор кадров не подтверждает вывод модели.')}</p>
  {busy?<div className="feature-loading" role="status"><Loader2 className="spin" size={18}/>{t('Извлекаем три кадра локально')}</div>:error?<div className="feature-warning" role="alert">{t(error)}</div>:<div className="replay-frames">{frames.map(frame=><button key={frame.role} className={frame.role==='moment'?'key-frame':''} onClick={()=>setZoom(frame)} aria-label={`${t('Увеличить кадр')} ${clock(frame.timestamp_sec)}`}><img src={`data:image/jpeg;base64,${frame.image_base64}`} alt={t(frame.role==='before'?'ДО':frame.role==='after'?'ПОСЛЕ':'МОМЕНТ')}/><span>{t(frame.role==='before'?'ДО':frame.role==='after'?'ПОСЛЕ':'МОМЕНТ')} <b>≈{clock(frame.timestamp_sec)}</b></span><ZoomIn size={15}/></button>)}</div>}
  <div className="replay-actions"><button className="context-button" onClick={()=>void playClip()} disabled={!file||clipBusy}><Play size={14}/>{t(clipBusy?'Готовим фрагмент':'Воспроизвести фрагмент')}</button><button className="context-button" disabled={!file} onClick={()=>onJump(timestamp)}>{t('К моменту в оригинале')}</button></div>
  {clipError&&<p className="feature-warning" role="alert">{t(clipError)}</p>}{clip&&<div className="replay-clip"><LocalVideo src={clip} autoPlay/><small>{t('Время плеера отсчитывается от начала фрагмента')}</small></div>}
  {zoom&&<div className="replay-modal" role="dialog" aria-modal="true" aria-label={t('Увеличить кадр')} onClick={()=>setZoom(null)}><button autoFocus aria-label={t('Закрыть')} onClick={()=>setZoom(null)}><X/></button><img src={`data:image/jpeg;base64,${zoom.image_base64}`} alt={`${t('Кадр')} ${clock(zoom.timestamp_sec)}`}/><span>{t('Исходная отметка')} ≈{clock(zoom.timestamp_sec)}</span></div>}
 </section>
}
