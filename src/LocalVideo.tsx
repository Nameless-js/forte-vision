import {useEffect,useRef,useState} from 'react';
import {Maximize,Pause,Play} from 'lucide-react';
import {useI18n} from './i18n';
import {clock} from './analysis';

// Custom controls keep browser-supplied labels from mixing interface languages.
export function LocalVideo({src,className='',autoPlay=false}:{src:string;className?:string;autoPlay?:boolean}){
 const {t}=useI18n();const ref=useRef<HTMLVideoElement>(null);const wrapper=useRef<HTMLDivElement>(null);const [playing,setPlaying]=useState(false);const [current,setCurrent]=useState(0);const [duration,setDuration]=useState(0);const [error,setError]=useState(false);
 useEffect(()=>{setPlaying(false);setCurrent(0);setDuration(0);setError(false)},[src]);
 async function toggle(){if(!ref.current)return;if(playing)ref.current.pause();else try{await ref.current.play()}catch{setError(true)}}
 return <div ref={wrapper} className={`local-video ${className}`}><video ref={ref} src={src} muted playsInline autoPlay={autoPlay} preload="metadata" onPlay={()=>setPlaying(true)} onPause={()=>setPlaying(false)} onTimeUpdate={event=>setCurrent(event.currentTarget.currentTime)} onLoadedMetadata={event=>{if(Number.isFinite(event.currentTarget.duration))setDuration(event.currentTarget.duration)}} onError={()=>setError(true)}/><div className="local-video-controls"><button aria-label={t(playing?'Пауза':'Воспроизвести')} onClick={()=>void toggle()}>{playing?<Pause size={15}/>:<Play size={15}/>}</button><span>{clock(current)} / {clock(duration)}</span><input aria-label={t('Временная шкала')} type="range" min="0" max={duration||1} step="0.1" value={Math.min(current,duration||1)} disabled={!duration} onChange={event=>{if(ref.current)ref.current.currentTime=Number(event.target.value)}}/><button aria-label={t('На весь экран')} onClick={()=>void wrapper.current?.requestFullscreen().catch(()=>{})}><Maximize size={14}/></button></div>{error&&<small className="feature-warning">{t('Браузер не поддерживает кодек этого видео. Для просмотра требуется совместимая MP4-копия; исходный MOV можно отправить в API.')}</small>}</div>
}
