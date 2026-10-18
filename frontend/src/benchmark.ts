import type {AnalysisResult} from './analysis';
export type CaseKind='original'|'new_angle'|'dark'|'blur'|'occlusion';
export type Truth=''|'violation'|'no_violation';
export type BenchCase={id:string;file:File;kind:CaseKind;source_id?:string;expected:Truth;expected_time:string;state:'idle'|'running'|'done'|'failed';result?:AnalysisResult;elapsed?:number;error?:string;sha256?:string;job_id?:string};
export const kindLabels:Record<CaseKind,string>={original:'Независимая запись',new_angle:'Другая камера',dark:'Затемнение',blur:'Размытие',occlusion:'Перекрытие'};
export function metrics(cases:BenchCase[]){
 const completed=cases.filter(c=>c.state==='done'&&c.result?.status==='done'&&!c.result.demo);
 const seen=new Set<string>();let duplicate_count=0;
 const unique=completed.filter(c=>{if(!c.sha256)return true;if(seen.has(c.sha256)){duplicate_count++;return false}seen.add(c.sha256);return true});
 const evaluated=unique.filter(c=>c.expected!=='');
 let tp=0,tn=0,fp=0,fn=0;const timing:number[]=[];
 for(const c of evaluated){const predicted=c.result!.verdict;
  if(c.expected==='violation'){if(predicted==='violation')tp++;else fn++}else if(predicted==='violation')fp++;else tn++;
  if(c.expected==='violation'&&predicted==='violation'&&c.expected_time.trim()!==''&&Number.isFinite(Number(c.expected_time))&&Number(c.expected_time)>=0&&c.result!.violations.length){timing.push(Math.min(...c.result!.violations.map(event=>Math.abs(event.timecode_sec-Number(c.expected_time)))))}
 }
 return {total:cases.length,completed:completed.length,evaluated:evaluated.length,duplicate_count,failed:cases.filter(c=>c.state==='failed').length,tp,tn,fp,fn,accuracy:evaluated.length?(tp+tn)/evaluated.length:null,timing_count:timing.length,mean_time_error:timing.length?timing.reduce((a,b)=>a+b,0)/timing.length:null};
}
export async function waitForJob(jobId:string,apiKey:string,signal:AbortSignal){
 const deadline=Date.now()+300000;
 while(Date.now()<deadline){
  const response=await fetch(`/api/v1/jobs/${encodeURIComponent(jobId)}`,{headers:{'X-API-Key':apiKey},signal});
  if(!response.ok)throw Error(response.status===401?'Неверный ключ API':'Не удалось получить статус задания');
  const result:AnalysisResult=await response.json();
  if(result.status==='done'){if(result.demo)throw Error('Стенд принимает только результаты модели');return result}
  if(result.status==='failed')throw Error(result.error?.includes('не подключена')?'Модель не подключена':'Ошибка обработки');
  await new Promise<void>((resolve,reject)=>{const stop=()=>{clearTimeout(timer);reject(new DOMException('Aborted','AbortError'))};const timer=setTimeout(()=>{signal.removeEventListener('abort',stop);resolve()},1000);signal.addEventListener('abort',stop,{once:true});if(signal.aborted)stop()});
 }
 throw Error('Превышено время ожидания: 5 минут.');
}
