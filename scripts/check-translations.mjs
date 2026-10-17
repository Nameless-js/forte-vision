import fs from 'node:fs';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {createRequire} from 'node:module';
const dictionary=JSON.parse(fs.readFileSync('src/translations.json','utf8'));
for(const [key,entry]of Object.entries(dictionary)){
 assert.deepEqual(Object.keys(entry).sort(),['en','kk','ru']);
 for(const language of ['en','kk','ru'])assert.ok(entry[language]?.trim(),`${key}: ${language}`);
 assert.ok(!/[А-Яа-яЁё]/.test(entry.en),`Russian text in English: ${key}`);
}
const compiled=await build({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {App} from './src/main';import {I18nProvider} from './src/i18n';export function render(language,theme,page){globalThis.testPage=page;globalThis.testResult=page==='workspace'?{job_id:'test',status:'done',demo:true,verdict:'violation',violations:[{type:'Исходный текст',description:'Исходный текст',timecode_sec:12,evidence_frames:[]}]}:null;globalThis.localStorage={getItem:key=>key==='blockwatch-language'?language:theme};return renderToStaticMarkup(React.createElement(I18nProvider,null,React.createElement(App)))}`,resolveDir:process.cwd(),loader:'tsx'},bundle:true,write:false,platform:'node',format:'cjs',plugins:[{name:'test-entry',setup(builder){builder.onLoad({filter:/src[\\/]main.tsx$/},({path})=>({contents:fs.readFileSync(path,'utf8').replace("useState<'home'|'workspace'>('home')","useState<'home'|'workspace'>(globalThis.testPage||'home')").replace('useState<Result|null>(null)','useState<Result|null>(globalThis.testResult)').replace(/createRoot\(document.getElementById\('root'\)!\)\.render\([\s\S]*$/, 'export {App};'),loader:'tsx'}));builder.onLoad({filter:/\.css$/},()=>({contents:'',loader:'js'}))}}]});
const module={exports:{}};new Function('require','module','exports',compiled.outputFiles[0].text)(createRequire(import.meta.url),module,module.exports);
for(const theme of ['bank','world'])for(const language of ['ru','kk','en'])for(const page of ['home','workspace']){
 const html=module.exports.render(language,theme,page);
 assert.ok(html.includes(dictionary['Загрузить видео'][language]));
 assert.ok(html.includes(dictionary['Как это работает'][language]));
 assert.ok(html.includes('language-select'));
 assert.equal(html.includes('nether-canvas'),theme==='world'&&page==='workspace','Nether scene must only render in the game workspace');
 assert.equal(html.includes('nether-portal-button'),theme==='world'&&page==='home','Portal entrance must only render on the Overworld home page');
 if(language==='en')assert.ok(!/[А-Яа-яЁё]/.test(html),'Russian leaked into English markup');
 if(page==='workspace')assert.ok(html.includes(dictionary['Открытое хранилище наличных'][language]));
 console.log(`PASS ${theme} / ${language} / ${page}`);
}
console.log(`PASS ${Object.keys(dictionary).length} complete translation entries`);

