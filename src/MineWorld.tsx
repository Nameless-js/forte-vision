import {useEffect,useRef,type ReactNode} from 'react';
import {useI18n} from './i18n';

function MineCanvas({animated}:{animated:boolean}){
 const ref=useRef<HTMLCanvasElement>(null);
 useEffect(()=>{
  const canvas=ref.current!,parent=canvas.parentElement!,ctx=canvas.getContext('2d')!,terrain=document.createElement('canvas');
  const preference=matchMedia('(prefers-reduced-motion: reduce)');let frame=0,last=0,visible=false;const started=performance.now();
  const noise=(x:number,y:number)=>{const n=Math.sin(x*127.1+y*311.7)*43758.5453;return n-Math.floor(n)};
  const rect=(x:number,y:number,w:number,h:number,color:string)=>{ctx.fillStyle=color;ctx.fillRect(Math.round(x),Math.round(y),Math.ceil(w),Math.ceil(h))};
  const line=(points:number[][],color:string,width=2)=>{ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.stroke()};
  const beam=(x:number,y:number,w:number,h:number)=>{rect(x,y,w,h,'#765137');rect(x+3,y+2,w-6,h-4,'#98704a');if(w>h){for(let i=9;i<w;i+=18){rect(x+i,y+4,10,3,'#b58b57');rect(x+i+4,y+h-6,7,2,'#5f402d')}}else{for(let i=8;i<h;i+=18){rect(x+4,y+i,w-8,3,'#66462e');rect(x+w-7,y+i+5,3,9,'#bd915d')}}rect(x,y,w,3,'#c39a6244');rect(x+w-3,y,3,h,'#3c2b25')};
  function paintTerrain(){const layer=terrain.getContext('2d')!,H=terrain.height;const rect=(x:number,y:number,w:number,h:number,color:string)=>{layer.fillStyle=color;layer.fillRect(Math.round(x),Math.round(y),Math.ceil(w),Math.ceil(h))};
   rect(0,0,960,H,'#25232b');
   // The surface ends in grass, soil, stone and finally deep slate.
   for(let y=0;y<H;y+=24)for(let x=0;x<960;x+=24){const n=noise(x,y);const soil=y<94;rect(x,y,24,24,soil?(n>.5?'#594333':'#4b382e'):y>1000?(n>.6?'#24232e':'#1c1d27'):(n>.7?'#39343a':n>.35?'#302c32':'#28272f'));rect(x+3,y+5,10,4,soil?'#99714b38':'#91858a16');rect(x+14,y+16,7,3,'#080c122b')}
   for(let x=0;x<960;x+=16){rect(x,0,16,9,x%3?'#567540':'#6a8548');rect(x,9,5,6,'#4b663a');if(noise(x,5)>.5)rect(x+8,9,7,10,'#405b32')}
   for(let y=130;y<H;y+=123)for(let x=0;x<960;x+=173){const n=noise(x,y);if(n<.3)continue;const color=y>700?'#62aeb4':n>.8?'#c5885c':'#8d8883';for(let i=0;i<5;i++){const xx=x+noise(i+x,y)*45,yy=y+noise(i+y,x)*35;rect(xx,yy,7,5,color);rect(xx+2,yy+1,3,2,y>700?'#a9d8cd':'#d0ad8066')}}
  }
  function draw(now:number){
   const moving=animated&&!preference.matches&&visible&&!document.hidden;if(moving&&now-last<55){frame=requestAnimationFrame(draw);return}last=now;const t=moving?(now-started)/1000:0,H=canvas.height;
   ctx.drawImage(terrain,0,0);
   // A cutaway tunnel recedes through three timber support frames.
   rect(107,215,746,418,'#15141bd9');rect(202,273,561,315,'#101117');rect(315,315,348,222,'#0c1016');rect(425,350,130,150,'#080d13');
   for(let i=0;i<8;i++){rect(115+i*94,240,83,5,'#433c3b55');rect(109+i*94,598,88,3,'#75604755')}
   beam(103,206,33,430);beam(824,206,33,430);beam(100,202,760,32);
   beam(227,272,24,320);beam(711,272,24,320);beam(223,267,516,26);
   beam(339,321,18,225);beam(608,321,18,225);beam(335,317,295,21);
   beam(426,355,13,159);beam(541,355,13,159);beam(424,351,133,15);
   // Sleepers and rails are perspective geometry, not a flat decoration.
   for(let i=0;i<13;i++){const p=i/12,yy=455+p*p*199,half=18+p*280;line([[490-half,yy],[490+half,yy]],'#72523b',7+p*7);line([[490-half,yy-2],[490+half,yy-2]],'#a77c4b',2)}
   line([[472,455],[224,656]],'#c0a390',5);line([[477,455],[231,656]],'#4d4848',2);line([[508,455],[756,656]],'#c0a390',5);line([[503,455],[749,656]],'#4d4848',2);
   // Warm lanterns illuminate the abandoned mineshaft.
   for(const [x,y,s]of [[174,263,1],[775,278,1],[286,327,.7],[666,330,.7],[386,368,.45]]){const sway=Math.sin(t*.8+x)*2;const glow=ctx.createRadialGradient(x,y+20,2,x,y+20,95*s);glow.addColorStop(0,'#f8ae4b36');glow.addColorStop(1,'#f8ae4b00');ctx.fillStyle=glow;ctx.fillRect(x-95*s,y-75*s,190*s,190*s);line([[x,y-28*s],[x+sway,y]],'#7d776b',2*s);rect(x-8*s+sway,y,16*s,21*s,'#393a3d');rect(x-5*s+sway,y+3*s,10*s,14*s,'#e8a549');rect(x-2*s+sway,y+5*s,4*s,10*s,'#ffe7a2');rect(x-10*s+sway,y+20*s,20*s,3*s,'#57504a')}
   // Minecart, crates, cobwebs and a forgotten pickaxe.
   rect(632,568,58,30,'#565359');rect(636,572,50,18,'#797277');rect(640,567,42,5,'#9e8b78');rect(637,598,10,8,'#292a32');rect(673,598,10,8,'#292a32');rect(645,560,9,8,'#33323a');rect(659,558,16,11,'#3d3940');
   beam(145,571,42,48);beam(149,575,34,5);beam(196,589,35,36);line([[198,549],[178,579]],'#a98a62',4);line([[182,548],[199,546],[210,554]],'#82928e',5);
   for(const [x,y,s]of [[138,237,1],[735,299,.7],[360,338,.5]]){ctx.globalAlpha=.38;for(let i=0;i<5;i++){const a=i*Math.PI/8;line([[x,y],[x+Math.cos(a)*58*s,y+Math.sin(a)*58*s]],'#d1d1c8',1)}for(let i=1;i<4;i++)line([[x+14*i*s,y],[x+12*i*s,y+12*i*s],[x,y+14*i*s]],'#d1d1c8',1);ctx.globalAlpha=1}
   for(let i=0;i<26;i++){const x=100+noise(i,32)*760+Math.sin(t*.3+i)*5,y=220+((noise(i,33)*400+t*(2+noise(i,34)*3))%400);ctx.globalAlpha=.12+noise(i,35)*.25;rect(x,y,2,2,'#e0caa1')}ctx.globalAlpha=1;
   const vignette=ctx.createLinearGradient(0,0,960,0);vignette.addColorStop(0,'#0d101a66');vignette.addColorStop(.5,'#0d101a00');vignette.addColorStop(1,'#0d101a66');ctx.fillStyle=vignette;ctx.fillRect(0,100,960,H-100);
   if(moving)frame=requestAnimationFrame(draw);
  }
  const restart=()=>{cancelAnimationFrame(frame);last=0;draw(performance.now())};
  const resize=()=>{canvas.width=960;canvas.height=Math.max(1100,Math.min(3200,Math.round(parent.getBoundingClientRect().height*960/Math.max(parent.clientWidth,1))));ctx.imageSmoothingEnabled=false;terrain.width=canvas.width;terrain.height=canvas.height;paintTerrain();restart()};
  const observer=new ResizeObserver(resize);observer.observe(parent);const intersection=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;restart()});intersection.observe(parent);document.addEventListener('visibilitychange',restart);preference.addEventListener('change',restart);resize();
  return()=>{cancelAnimationFrame(frame);observer.disconnect();intersection.disconnect();document.removeEventListener('visibilitychange',restart);preference.removeEventListener('change',restart)};
 },[animated]);
 return <canvas ref={ref} className="mine-canvas" aria-hidden="true"/>;
}

export function Underground({enabled,animated,children}:{enabled:boolean;animated:boolean;children:ReactNode}){return enabled?<div className="underground"><MineCanvas animated={animated}/>{children}</div>:<>{children}</>}
export function MineIntro(){const {t}=useI18n();return <section className="mine-descent" aria-label={t('Заброшенная шахта')}><div className="mine-sign"><span>{t('НИЖЕ ПОВЕРХНОСТИ')}</span><h2>{t('Заброшенная шахта')}</h2><p>{t('Самое важное часто скрыто глубже.')}</p></div><div className="mine-depth"><span>↓</span>{t('ГЛУБИНА: 32 БЛОКА')}</div></section>}
