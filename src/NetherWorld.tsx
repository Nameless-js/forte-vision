import {useEffect,useRef,type CSSProperties} from 'react';
import {useI18n} from './i18n';

export function NetherWorld({animated}:{animated:boolean}){
 const ref=useRef<HTMLCanvasElement>(null);const {t}=useI18n();
 useEffect(()=>{
  const canvas=ref.current!,ctx=canvas.getContext('2d')!;canvas.width=960;canvas.height=640;ctx.imageSmoothingEnabled=false;
  const preference=matchMedia('(prefers-reduced-motion: reduce)');let frame=0,last=0,visible=!document.hidden;const start=performance.now();
  const random=(a:number,b:number)=>{const n=Math.sin(a*127.1+b*311.7)*43758.5453;return n-Math.floor(n)};
  const rect=(x:number,y:number,w:number,h:number,color:string)=>{ctx.fillStyle=color;ctx.fillRect(Math.round(x),Math.round(y),Math.ceil(w),Math.ceil(h))};
  const polygon=(points:number[][],color:string)=>{ctx.fillStyle=color;ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fill()};
  const rock=(x:number,y:number,w:number,h:number,seed:number,light=false)=>{rect(x,y,w,h,light?'#4b3034':'#30232c');for(let yy=0;yy<h;yy+=12)for(let xx=0;xx<w;xx+=14){const n=random(xx+seed,yy+seed);rect(x+xx+2,y+yy+2,9,6,n>.8?'#77504b':n>.45?'#40252e':'#211d26')}rect(x,y,3,h,'#83504b30')};
  function draw(now:number){
   const moving=animated&&!preference.matches&&visible;const time=moving?(now-start)/1000:0;
   if(moving&&now-last<45){frame=requestAnimationFrame(draw);return}last=now;
   const sky=ctx.createLinearGradient(0,0,0,640);sky.addColorStop(0,'#170d1d');sky.addColorStop(.45,'#52202b');sky.addColorStop(.76,'#993b28');sky.addColorStop(1,'#e16c27');ctx.fillStyle=sky;ctx.fillRect(0,0,960,640);
   // Cavern ceiling, receding basalt deltas and an unbroken lava sea.
   for(let layer=0;layer<3;layer++)for(let x=0;x<960;x+=18){const height=45+random(x,layer)*70;rect(x,0,19,height,['#291520','#311a24','#3b2028'][layer]);if(x%54===0)rect(x+4,height,8,20+random(x,4)*42,'#3b2028')}
   for(let layer=0;layer<3;layer++){const base=350+layer*55;for(let x=-20;x<980;x+=22){const height=30+random(Math.floor(x/50),layer+8)*100;rect(x,base-height,23,640-base+height,['#542630','#542730','#4c252b'][layer])}}
   rect(0,438,960,202,'#cd4e20');
   for(let row=0;row<30;row++){const y=440+row*7;for(let column=0;column<28;column++){const x=column*37+Math.sin(time*.3+row)*8;const n=random(column,row);rect(x,y,12+n*25,2+row*.06,Math.sin(time+column+row)>.5?'#ffb240':'#ed7426');if(n>.85)rect(x+8,y+3,9,2,'#ffe297')}}
   // Lava streams descend from cracks in the roof and glow through the haze.
   for(const [x,top,width,bottom]of [[315,116,11,472],[772,58,14,450],[897,146,7,477]]){const glow=ctx.createLinearGradient(x-25,0,x+width+25,0);glow.addColorStop(0,'#ff7f2600');glow.addColorStop(.5,'#ff83264a');glow.addColorStop(1,'#ff7f2600');ctx.fillStyle=glow;ctx.fillRect(x-25,top,width+50,bottom-top);rect(x,top,width,bottom-top,'#ee6a21');rect(x+3,top,Math.max(2,width-6),bottom-top,'#ffc357');for(let i=0;i<16;i++)rect(x,top+(i*27+time*25)%(bottom-top),width,3,'#e94b1f')}
   // Blackstone fortress: towers, crenellations and a bridge above the lava.
   rock(592,280,72,220,20);rock(810,245,64,245,24);rock(634,355,194,30,17);
   for(let i=0;i<6;i++){rect(586+i*15,267,10,20,'#38232b');rect(806+i*14,231,9,20,'#38232b')}
   for(let i=0;i<7;i++){rect(647+i*25,385,10,75,'#352129');rect(643+i*25,382,18,9,'#40252d')}
   for(const [x,y]of [[611,313],[831,286]]){rect(x,y,18,30,'#160f1b');rect(x+3,y+4,12,23,'#f18b39');rect(x+6,y+7,5,19,'#ffce69')}
   // A distant, softly rippling obsidian portal anchors the other side.
   rock(706,299,57,104,33);rect(717,309,35,82,'#5e20a0');for(let i=0;i<15;i++){ctx.globalAlpha=.22;rect(719+random(i,6)*29,311+((i*13+time*9)%75),3,9,'#e3a0ff')}ctx.globalAlpha=1;rect(704,400,62,7,'#2d1c29');
   // Basalt columns and mineral veins on the foreground shores.
   for(let i=0;i<13;i++){const x=i*24-65,y=415+random(i,4)*160;rock(x,y,24,640-y,i, i%3===0);rect(x+3,y,20,4,'#79605e');if(i%4===0)for(let j=0;j<4;j++)rect(x+7,y+20+j*17,5,3,'#f09b3c')}
   polygon([[680,575],[735,548],[797,557],[840,527],[960,545],[960,640],[640,640]],'#43232c');
   for(let i=0;i<22;i++){const x=690+random(i,22)*270,y=570+random(i,23)*70;rect(x,y,14,3,i%3?'#67313a':'#ee8c3b')}
   // Crimson fungi, soul fire and a wandering magma cube.
   for(const [x,y,s]of [[918,552,1],[763,587,.6],[243,569,.8]]){rect(x,y-27*s,7*s,29*s,'#6f3440');rect(x-18*s,y-38*s,44*s,13*s,'#b83f45');rect(x-12*s,y-45*s,31*s,8*s,'#d2564f');rect(x-9*s,y-36*s,5*s,4*s,'#f49b63');rect(x+13*s,y-37*s,4*s,3*s,'#f49b63')}
   const cubeY=572-Math.max(0,Math.sin(time*1.5))*13;rect(839,cubeY,24,21,'#65292e');rect(841,cubeY+2,20,4,'#f27d2b');rect(841,cubeY+10,20,3,'#e85d23');rect(844,cubeY+6,4,4,'#ffe48d');rect(854,cubeY+6,4,4,'#ffe48d');
   for(const [x,y]of [[237,555],[886,546]]){rect(x,y,17,5,'#453c3a');polygon([[x+2,y],[x+3,y-18-Math.sin(time*7)*4],[x+9,y-9],[x+13,y-22],[x+16,y]],'#47b7bb');polygon([[x+5,y],[x+8,y-15],[x+12,y]],'#a9f0e0')}
   // A ghast drifts through the distant cavern; no external assets required.
   const gx=452+Math.sin(time*.19)*48,gy=206+Math.sin(time*.55)*9;ctx.globalAlpha=.44;rect(gx,gy,38,34,'#ceb7ad');rect(gx+5,gy+4,27,23,'#edcfc0');rect(gx+8,gy+14,5,4,'#68404a');rect(gx+25,gy+14,5,4,'#68404a');rect(gx+16,gy+24,6,3,'#97626b');for(let i=0;i<5;i++)rect(gx+3+i*7,gy+33,4,10+Math.sin(time*2+i)*5,'#b79c99');ctx.globalAlpha=1;
   // Rising embers and ash cover the whole viewport at a capped frame rate.
   for(let i=0;i<75;i++){const x=random(i,43)*960+Math.sin(time*.4+i)*12,y=640-((random(i,44)*700+time*(7+random(i,45)*18))%700);ctx.globalAlpha=.2+random(i,46)*.5;rect(x,y,i%9===0?3:1,i%9===0?3:2,i%4?'#f5ab72':'#c3b7b1')}ctx.globalAlpha=1;
   const shade=ctx.createLinearGradient(0,0,960,0);shade.addColorStop(0,'#130c18b0');shade.addColorStop(.5,'#190e1845');shade.addColorStop(1,'#1a0e1822');ctx.fillStyle=shade;ctx.fillRect(0,0,960,640);
   if(moving)frame=requestAnimationFrame(draw);
  }
  const restart=()=>{cancelAnimationFrame(frame);visible=!document.hidden;draw(performance.now())};document.addEventListener('visibilitychange',restart);preference.addEventListener('change',restart);draw(performance.now());
  return()=>{cancelAnimationFrame(frame);document.removeEventListener('visibilitychange',restart);preference.removeEventListener('change',restart)};
 },[animated]);
 return <canvas ref={ref} className="world-canvas nether-canvas" aria-label={t('Живой Незер: лавовое море, крепость, базальт и багровые грибы')}/>;
}

export function PortalButton({onClick}:{onClick:()=>void}){
 const {t}=useI18n();
 return <button className="nether-portal-button" onClick={onClick} aria-label={t('Загрузить видео')}><span className="portal-field" aria-hidden="true"><i/><i/><i/><i/><i/><i/></span><span className="portal-button-copy"><small>{t('ПОРТАЛ В НЕЗЕР')}</small><strong>{t('Загрузить видео')}</strong><span>{t('Нажмите, чтобы переместиться')} <b>↗</b></span></span><span className="portal-sparks" aria-hidden="true">✦<i>✧</i><b>✦</b></span></button>
}

export function PortalTravel(){const {t}=useI18n();return <div className="portal-travel" role="status" aria-live="polite"><div className="portal-travel-noise"/><div className="portal-tunnel" aria-hidden="true">{Array.from({length:7},(_,i)=><i key={i} style={{'--gate':i} as CSSProperties}/>)}</div><div className="portal-travel-copy"><span>▥</span><small>{t('Входим в Незер…')}</small></div></div>}
