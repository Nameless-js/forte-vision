import {useI18n} from './i18n';
import {ArrowUpRight, Eye, ShieldCheck, ScanLine} from 'lucide-react';

export function BankVisual(){
 const {t}=useI18n();
 return <div className="bank-visual" aria-label={t("ViBank — визуальный контроль с проверяемым результатом")}>
  <div className="bank-visual-grid"/>
  <div className="visual-coordinate coordinate-top">ViBank <span>{t("01 / OBSERVE")}</span></div>
  <div className="vision-orbit orbit-one"/><div className="vision-orbit orbit-two"/>
  <div className="vision-object"><div className="vision-rim"><div className="vision-aperture"><Eye strokeWidth={.8}/><div className="aperture-light"/></div></div><div className="object-reflection"/></div>
  <div className="visual-note note-local"><span><ShieldCheck size={15}/></span><div>{t("Локальный контур")}<small>{t("Данные под вашим контролем")}</small></div></div>
  <div className="visual-note note-evidence"><span><ScanLine size={16}/></span><div>{t("От события к основанию")}<small>{t("Кадр · Контекст · Правило")}</small></div><ArrowUpRight size={16}/></div>
  <div className="visual-coordinate coordinate-bottom"><span className="visual-dot"/>  {t("ВНИМАНИЕ К КАЖДОЙ ДЕТАЛИ")} <span>{t("HUMAN IN CONTROL")}</span></div>
 </div>
}
