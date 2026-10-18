import {createContext,useContext,useEffect,useState,type ReactNode} from 'react';
import translations from './translations.json';
export type Language='ru'|'kk'|'en';
const dictionary:Record<string,Record<Language,string>>=translations;
const originals=new Map<string,string>();
for(const [key,entry] of Object.entries(dictionary))for(const value of Object.values(entry))originals.set(value,key);
const Context=createContext<{language:Language;setLanguage:(language:Language)=>void;t:(key:string)=>string}>({language:'ru',setLanguage:()=>{},t:key=>key});
export function I18nProvider({children}:{children:ReactNode}){
 const [language,setLanguage]=useState<Language>(()=>{try{const saved=localStorage.getItem('blockwatch-language');return saved==='kk'||saved==='en'?saved:'ru'}catch{return 'ru'}});
 useEffect(()=>{document.documentElement.lang=language;try{localStorage.setItem('blockwatch-language',language)}catch{}},[language]);
 const t=(key:string)=>dictionary[key]?.[language]??dictionary[originals.get(key)??'']?.[language]??key;
 return <Context.Provider value={{language,setLanguage,t}}>{children}</Context.Provider>;
}
export const useI18n=()=>useContext(Context);
