import {Check,HelpCircle,ShieldQuestion,X} from 'lucide-react';
import {useI18n} from './i18n';
import {checkDefinitions,clock,type AnalysisEvent,type CheckStatus,type HumanReview} from './analysis';
const labels={confirmed:'Подтверждено',refuted:'Опровергнуто',unknown:'Не установлено'};
export function CounterChecks({event,review,onChange,onJump,demo}:{event:AnalysisEvent;review?:HumanReview;onChange:(review:HumanReview)=>void;onJump:(time:number)=>void;demo:boolean}){
 const {t,language}=useI18n();
 const update=(patch:Partial<HumanReview>)=>onChange({checks:review?.checks||{},note:review?.note||'',...patch,updated_at:new Date().toISOString()});
 const alternative=event.checks?.find(check=>check.id==='alternative_explanation');
 return <section className="counter-checks" aria-label={t('Проверка гипотезы')}>
  <div className="feature-section-title"><span><ShieldQuestion size={18}/>{t('Что может опровергнуть вывод?')}</span></div>
  <p className="feature-help">{t('Сопоставьте наблюдения модели с видео. Отметки проверяющего сохраняются отдельно от автоматического результата.')}</p>
  {alternative?.status==='confirmed'&&!demo&&<p className="feature-warning">{t('Модель отметила альтернативное объяснение. Пересмотрите первоначальный вывод.')}</p>}
  <div className="check-column-headings"><span>{t('Условие и наблюдение модели')}</span><span>{t('Ваша проверка')}</span></div>
  {checkDefinitions.map(definition=>{const observation=demo?undefined:event.checks?.find(check=>check.id===definition.id);const status=observation?.status||'unknown';const note=observation?.translations?.[language]||(language==='ru'?observation?.note:undefined);return <div className="observation-check" key={definition.id}>
   <div><strong>{t(definition.label)}</strong><small>{t(definition.hint)}</small><span className={`check-state ${status}`}>{status==='confirmed'?<Check size={13}/>:status==='refuted'?<X size={13}/>:<HelpCircle size={13}/>} {t(labels[status])}</span>{note&&<p>{note}</p>}{!observation&&<small>{t('Модель не передала наблюдение')}</small>}{observation?.timestamp_sec!==undefined&&<button className="context-button" onClick={()=>onJump(observation.timestamp_sec!)}>{clock(observation.timestamp_sec)}</button>}</div>
   <select aria-label={`${t('Ваша проверка')}: ${t(definition.label)}`} value={review?.checks[definition.id]||'unknown'} onChange={e=>update({checks:{...review?.checks,[definition.id]:e.target.value as CheckStatus}})}>{Object.entries(labels).map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</select>
  </div>})}
  <label className="review-note">{t('Комментарий проверяющего')}<textarea maxLength={2000} value={review?.note||''} onChange={e=>update({note:e.target.value})} placeholder={t('Какой видимый факт подтверждает или опровергает объяснение?')}/></label>
  <small className="feature-help">{t('Ручная проверка входит в экспорт отчёта. Вердикт модели не изменяется.')}</small>
 </section>
}
