import {useState} from 'react';
import BasicDropdown from './accordion-2';

export default function DropdownDemo() {
  const [value,setValue]=useState('medium');
  const items=['small','medium','large','extra-large'].map(id=>({id,label:id,text:id}));
  return <div className="bank-mode" style={{padding:32}}>
    <div style={{maxWidth:280}}><BasicDropdown label="Select a size" items={items} value={value} onChange={item=>setValue(item.id)}/></div>
  </div>;
}
