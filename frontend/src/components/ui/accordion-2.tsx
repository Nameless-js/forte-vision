import {revealDropdownOption} from './dropdown-scroll';
import {Children, createContext, isValidElement, useContext, useEffect, useId, useLayoutEffect, useRef, useState} from 'react';
import type {CSSProperties, KeyboardEvent, ReactElement, ReactNode, SelectHTMLAttributes} from 'react';
import {createPortal} from 'react-dom';
import {Check, ChevronDown} from 'lucide-react';
import {AnimatePresence, LazyMotion, domAnimation, m, useReducedMotion} from 'framer-motion';
import './bank-select.css';

export const BankSelectContext = createContext(false);
export interface DropdownItem {id: string; label: ReactNode; text: string; disabled?: boolean; icon?: ReactNode}
interface DropdownProps {label: string; items: DropdownItem[]; value: string; disabled?: boolean; className?: string; onChange: (item: DropdownItem) => void; labelId?: string}

export default function BasicDropdown({label, items, value, disabled, className='', onChange, labelId}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [position, setPosition] = useState<CSSProperties>({});
  const button = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const id = useId();
  const reduced = useReducedMotion();
  const selected = items.find(item => item.id === value);
  const search = useRef({text: '', time: 0});
  const close = () => setOpen(false);
  const choose = (index: number) => {
    const item = items[index];
    if (!item || item.disabled) return;
    onChange(item); close(); button.current?.focus({preventScroll:true});
  };
  const show = () => {
    if (disabled) return;
    setActive(Math.max(0, items.findIndex(item => item.id === value && !item.disabled)));
    setOpen(true);
  };
  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const rect = button.current?.getBoundingClientRect();
      if (!rect) return;
      const down = window.innerHeight - rect.bottom - 12;
      const up = rect.top - 12;
      const above = down < 180 && up > down;
      const width = Math.min(Math.max(rect.width, 160), window.innerWidth - 16);
      setPosition({position:'fixed', left:Math.max(8, Math.min(rect.left, window.innerWidth-width-8)), width,
        maxHeight: Math.max(60, Math.min(280, above?up:down)),
        ...(above?{bottom:window.innerHeight-rect.top+6}:{top:rect.bottom+6}), transformOrigin:above?'bottom':'top'});
    };
    place();
    const outside = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!button.current?.contains(target) && !menu.current?.contains(target)) close();
    };
    const scroll = (event: Event) => {if (!menu.current?.contains(event.target as Node)) close();};
    document.addEventListener('pointerdown', outside);
    window.addEventListener('resize', place);
    document.addEventListener('scroll', scroll, true);
    return () => {document.removeEventListener('pointerdown', outside); window.removeEventListener('resize', place); document.removeEventListener('scroll', scroll, true);};
  }, [open]);
  useEffect(() => {if(disabled) close();}, [disabled]);
  useLayoutEffect(() => {
    if(open && menu.current) revealDropdownOption(menu.current, active);
  }, [active, open, position.maxHeight]);
  const keyboard = (event: KeyboardEvent<HTMLButtonElement>) => {
    const enabled = items.map((item,index) => item.disabled?-1:index).filter(index=>index>=0);
    if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
      event.preventDefault();
      if (!open) {show(); if(event.key==='End')setActive(enabled.at(-1)??0); return;}
      const index = enabled.indexOf(active);
      setActive(event.key==='Home'?enabled[0]??0:event.key==='End'?enabled.at(-1)??0:enabled[(index+(event.key==='ArrowDown'?1:-1)+enabled.length)%enabled.length]??0);
    } else if(event.key==='Enter'||event.key===' ') {event.preventDefault(); if(open) choose(active);else show();}
    else if(event.key==='Escape') {event.preventDefault();close();}
    else if(event.key==='Tab') close();
    else if(event.key.length===1&&!event.ctrlKey&&!event.metaKey&&!event.altKey) {
      search.current={text:(Date.now()-search.current.time<600?search.current.text:'')+event.key.toLocaleLowerCase(),time:Date.now()};
      const index=items.findIndex(item=>!item.disabled&&item.text.toLocaleLowerCase().startsWith(search.current.text));
      if(index>=0){event.preventDefault(); if(!open)show();setActive(index);}
    }
  };
  const host = button.current?.closest('.bank-mode');
  return <LazyMotion features={domAnimation}><span className={`bank-select ${className}`}>
    <button ref={button} type="button" className="bank-select-trigger" role="combobox" aria-label={label||undefined} aria-labelledby={labelId} aria-haspopup="listbox" aria-expanded={open&&!disabled} aria-controls={open?id:undefined} aria-activedescendant={open?`${id}-${active}`:undefined} disabled={disabled} onClick={()=>open?close():show()} onKeyDown={keyboard} onBlur={close}>
      <span>{selected?.label??label}</span><ChevronDown size={16} className={open?'is-open':''} aria-hidden="true"/>
    </button>
    {host&&createPortal(<AnimatePresence>{open&&!disabled&&<m.div ref={menu} id={id} role="listbox" aria-label={label||undefined} aria-labelledby={labelId} className="bank-select-menu" style={position}
      initial={reduced?false:{opacity:0,y:-8,scaleY:.96}} animate={{opacity:1,y:0,scaleY:1}} exit={{opacity:0,y:reduced?0:-5,scaleY:reduced?1:.98}} transition={{duration:reduced?0:.18,ease:'easeOut'}}>
      {items.map((item,index)=><div key={item.id} id={`${id}-${index}`} role="option" aria-selected={item.id===value} aria-disabled={item.disabled||undefined} data-index={index} className={`bank-select-option ${index===active?'is-active':''} ${item.id===value?'is-selected':''}`} onPointerMove={()=>!item.disabled&&setActive(index)} onMouseDown={event=>event.preventDefault()} onClick={()=>choose(index)}>
        {item.icon}<span>{item.label}</span>{item.id===value&&<Check size={16} aria-hidden="true"/>}
      </div>)}
    </m.div>}</AnimatePresence>,host)}
  </span></LazyMotion>;
}

type Props = SelectHTMLAttributes<HTMLSelectElement>;
function options(children: ReactNode): DropdownItem[] {
  return Children.toArray(children).flatMap(child=>{
    if (!isValidElement(child)) return [];
    const option=child as ReactElement<{value?: string|number; children?: ReactNode; disabled?: boolean}>;
    if(option.type!=='option')return options(option.props.children);
    const text=Children.toArray(option.props.children).join('');
    return [{id:String(option.props.value??text),label:option.props.children,text,disabled:option.props.disabled}];
  });
}

export function Select(props: Props) {
  const bank=useContext(BankSelectContext);
  const native=useRef<HTMLSelectElement>(null);
  const [uncontrolled,setUncontrolled]=useState(String(props.defaultValue??''));
  const [label,setLabel]=useState('');
  useLayoutEffect(()=>{
    const parent=native.current?.labels?.[0];
    setLabel(parent?Array.from(parent.childNodes).filter(node=>node.nodeType===Node.TEXT_NODE).map(node=>node.textContent).join('').trim():'');
  },[bank,props.children]);
  if(!bank)return <select {...props}/>;
  const items=options(props.children);
  const value=String(props.value??(uncontrolled||(items[0]?.id??'')));
  return <span className="bank-select-field">
    <select {...props} ref={native} className="bank-select-native" tabIndex={-1} aria-hidden="true"/>
    <BasicDropdown label={props['aria-label']??label} labelId={props['aria-labelledby']} items={items} value={value} disabled={props.disabled} className={props.className} onChange={item=>{
      setUncontrolled(item.id);
      if(native.current){native.current.value=item.id;native.current.dispatchEvent(new Event('change',{bubbles:true}));}
    }}/>
  </span>;
}
