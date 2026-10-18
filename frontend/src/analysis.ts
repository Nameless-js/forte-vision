export type Evidence={timestamp_sec:number;image_base64:string};
export type CheckId='subject_visible'|'object_state_visible'|'action_sequence'|'alternative_explanation';
export type CheckStatus='confirmed'|'refuted'|'unknown';
export type ObservationCheck={id:CheckId;status:CheckStatus;note?:string;timestamp_sec?:number;translations?:Partial<Record<'ru'|'kk'|'en',string>>};
export type AnalysisEvent={translations?:Partial<Record<'ru'|'kk'|'en',{type:string;description:string;rule?:{title:string;section:string;url:string}}>>;type:string;timecode_sec:number;description:string;evidence_frames:Evidence[];checks?:ObservationCheck[];rule?:{title:string;section:string;url:string};end_sec?:number};
export type AnalysisResult={progress?:number;stage?:string;duration_sec?:number;job_id:string;status:'processing'|'done'|'failed';verdict?:'violation'|'no_violation';violations:AnalysisEvent[];error?:string;demo?:boolean};
export type HumanReview={checks:Partial<Record<CheckId,CheckStatus>>;note:string;updated_at:string};
export const checkDefinitions:{id:CheckId;label:string;hint:string}[]=[
 {id:'subject_visible',label:'Участник действия виден',hint:'Можно проследить положение участника в нужный момент.'},
 {id:'object_state_visible',label:'Состояние объекта различимо',hint:'Открытие, закрытие или положение объекта действительно видно.'},
 {id:'action_sequence',label:'Последовательность подтверждена',hint:'Контекст до и после согласуется с описанием события.'},
 {id:'alternative_explanation',label:'Есть видимая альтернативная причина',hint:'Проверьте контекст, который может опровергнуть первоначальное объяснение.'},
];
export const clock=(n:number)=>`${Math.floor(n/60).toString().padStart(2,'0')}:${(n%60).toFixed(1).padStart(4,'0')}`;
export function downloadJSON(value:unknown,name:string){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
export function mediaError(status:number){return status===401?'Неверный ключ API':status===429?'Медиасервис занят':status===413?'Файл больше 100 МБ. Выберите файл меньшего размера.':'Не удалось обработать видео локально'}
export function safeError(error:unknown){const known=['Неверный ключ API','Медиасервис занят','Файл больше 100 МБ. Выберите файл меньшего размера.','Не удалось обработать видео локально','Не удалось получить статус задания','Модель не подключена','Ошибка обработки','Превышено время ожидания: 5 минут.','Стенд принимает только результаты модели'];return error instanceof Error&&known.includes(error.message)?error.message:'Ошибка соединения'}
