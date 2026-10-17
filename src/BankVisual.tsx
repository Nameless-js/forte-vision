import {ArrowUpRight, Eye, ShieldCheck, ScanLine} from 'lucide-react';

export function BankVisual(){
 return <div className="bank-visual" aria-label="Forte Vision — визуальный контроль с проверяемым результатом">
  <div className="bank-visual-grid"/>
  <div className="visual-coordinate coordinate-top">FORTE VISION <span>01 / OBSERVE</span></div>
  <div className="vision-orbit orbit-one"/><div className="vision-orbit orbit-two"/>
  <div className="vision-object"><div className="vision-rim"><div className="vision-aperture"><Eye strokeWidth={.8}/><div className="aperture-light"/></div></div><div className="object-reflection"/></div>
  <div className="visual-note note-local"><span><ShieldCheck size={15}/></span><div>Локальный контур<small>Данные под вашим контролем</small></div></div>
  <div className="visual-note note-evidence"><span><ScanLine size={16}/></span><div>От события к основанию<small>Кадр · Контекст · Правило</small></div><ArrowUpRight size={16}/></div>
  <div className="visual-coordinate coordinate-bottom"><span className="visual-dot"/> ВНИМАНИЕ К КАЖДОЙ ДЕТАЛИ <span>HUMAN IN CONTROL</span></div>
 </div>
}
