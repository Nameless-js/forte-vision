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
   // Side-on cutaway: horizontal galleries, cross shafts and separate floors.
   rect(18,232,924,115,'#11151d');rect(118,208,254,25,'#151820');rect(570,217,313,16,'#151820');
   rect(20,391,918,107,'#11151d');rect(283,367,321,25,'#151820');
   rect(43,548,880,94,'#10151d');rect(405,238,130,382,'#0c1119');
   // Broken stone lips make the excavations look carved from blocks.
   for(let x=17;x<942;x+=24){const n=noise(x,12);if(n>.5)rect(x,230,24,7,'#3b353b');if(n>.7)rect(x+5,384,18,9,'#3f383d');rect(x,347,24,12,n>.5?'#4c4342':'#39353c');rect(x,498,24,14,n>.5?'#4a4141':'#36353c');if(x>40&&x<920)rect(x,642,24,15,n>.5?'#403b42':'#34313b')}
   // Vertical shaft, ladders and a timber bridge connect the galleries.
   rect(412,347,116,15,'#0c1119');beam(404,497,134,11);
   line([[458,250],[458,631]],'#967044',4);line([[477,250],[477,631]],'#967044',4);for(let y=255;y<629;y+=17)rect(456,y,24,4,'#b28a55');
   const support=(x:number,top:number,floor:number,w=133)=>{beam(x,top,11,floor-top);beam(x+w,top,11,floor-top);beam(x-4,top-10,w+19,13);rect(x-5,floor-4,21,6,'#b58a5a');rect(x+w-5,floor-4,21,6,'#b58a5a')};
   for(const x of [39,219,585,774])support(x,245,347,130);
   for(const x of [55,270,616,793])support(x,401,498,116);
   for(const x of [79,292,573,767])support(x,558,642,118);
   // Rails run horizontally across the section, with sleepers and a broken end.
   for(let x=24;x<894;x+=19){rect(x,493,12,5,'#9a754e');rect(x+2,495,8,3,'#5e4635')}
   rect(22,488,872,3,'#9d9691');rect(22,491,872,2,'#51494a');rect(22,496,872,2,'#b4a08b');line([[894,488],[921,501]],'#b4a08b',3);
   // Ore seams embedded in the exposed stone, not floating in the corridor.
   for(const [x,y,color]of [[87,177,'#cc9b65'],[278,363,'#dcb364'],[665,518,'#6bc0c3'],[850,189,'#958b83'],[286,602,'#60c7cf'],[538,549,'#b34c50']] as const){for(let i=0;i<7;i++){const xx=x+noise(i,x)*29,yy=y+noise(i,y)*22;rect(xx,yy,6,5,color);rect(xx+1,yy,2,2,'#e4dec366')}}
   // Lanterns swing from crossbeams; torches flicker along the stone walls.
   for(const [x,y]of [[113,251],[675,252],[342,407],[856,407],[640,563]]){const sway=Math.sin(t*.8+x)*1.5;line([[x,y-11],[x+sway,y+7]],'#79736c',2);const glow=ctx.createRadialGradient(x,y+16,1,x,y+16,66);glow.addColorStop(0,'#ffc26532');glow.addColorStop(1,'#ffc26500');ctx.fillStyle=glow;ctx.fillRect(x-66,y-50,132,132);rect(x-6+sway,y+7,13,18,'#55514d');rect(x-4+sway,y+10,9,12,'#eeb65a');rect(x-1+sway,y+11,3,9,'#ffe9b0');rect(x-8+sway,y+24,17,3,'#71614d')}
   const torch=(x:number,y:number)=>{const glow=ctx.createRadialGradient(x,y,1,x,y,53);glow.addColorStop(0,'#ffb65536');glow.addColorStop(1,'#ffb65500');ctx.fillStyle=glow;ctx.fillRect(x-53,y-53,106,106);rect(x-1,y+3,4,13,'#987047');rect(x-3,y-6,8,11,'#e48d38');rect(x-1,y-9+Math.floor(t*6)%3,4,10,'#ffe19b')};torch(365,304);torch(573,461);torch(140,604);torch(881,608);
   // Cobwebs cling to support corners and span disused openings.
   const web=(x:number,y:number,w:number,h:number)=>{ctx.globalAlpha=.42;for(let i=0;i<5;i++)line([[x,y],[x+w*(1-i/4),y+h*i/4]],'#d5d0c1',1);for(let i=1;i<5;i++){const p=i/4;line([[x+w*p,y],[x+w*p*.76,y+h*p*.24],[x+w*p*.48,y+h*p*.52],[x+w*p*.22,y+h*p*.78],[x,y+h*p]],'#d5d0c1',1)}ctx.globalAlpha=1};
   web(232,246,57,50);web(789,247,47,47);web(68,405,47,40);web(628,404,54,49);web(306,561,46,48);web(781,561,38,39);
   // A minecart rolls along the middle gallery; its wheels turn with travel.
   const cartX=657+Math.sin(t*.24)*46;rect(cartX-25,464,50,25,'#51535b');rect(cartX-21,467,42,15,'#878087');rect(cartX-27,462,54,5,'#a89b8b');rect(cartX-13,456,11,7,'#34363d');rect(cartX+2,452,13,11,'#444149');
   for(const x of [cartX-15,cartX+15]){rect(x-4,486,8,8,'#222732');rect(x-2,488,4,4,'#8e8e8c');const d=Math.sin(t*4)>0?2:-2;line([[x-d,489],[x+d,491]],'#b9a58a',1)}
   // Zombie wanders along the upper level, drawn in profile.
   const zombieX=318+Math.sin(t*.28)*31,zombieY=347,walk=Math.sin(t*3)*3;ctx.save();ctx.translate(zombieX,zombieY);ctx.scale(Math.cos(t*.28)>=0?1:-1,1);rect(-6,-14,5,14+walk,'#39355b');rect(2,-14,5,14-walk,'#2c3156');rect(-7,-33,16,20,'#337579');rect(-7,-31,4,17,'#315d59');rect(7,-30,14,5,'#789a58');rect(17,-32,5,7,'#789a58');rect(-7,-48,16,15,'#79985b');rect(-7,-48,16,4,'#526e45');rect(5,-42,3,3,'#253d34');rect(4,-36,5,2,'#465d40');ctx.restore();
   // Creeper waits in a darker alcove on the middle level.
   const cx=842,cy=497+Math.sin(t*.7)*.5;rect(cx-8,cy-9,6,9,'#415840');rect(cx+3,cy-9,6,9,'#354c3b');rect(cx-6,cy-28,13,20,'#668454');rect(cx-9,cy-44,19,17,'#85a66b');rect(cx-9,cy-44,19,4,'#698957');rect(cx-6,cy-38,4,4,'#25392b');rect(cx+3,cy-38,4,4,'#25392b');rect(cx-2,cy-34,5,5,'#25392b');rect(cx-5,cy-31,4,5,'#25392b');rect(cx+2,cy-31,4,5,'#25392b');
   // Cave spider scuttles beneath the top gallery's cobwebs.
   const spiderX=650+Math.sin(t*.42)*25,spiderY=338;for(let i=0;i<4;i++){const step=Math.sin(t*4+i)*3;line([[spiderX-5,spiderY],[spiderX-13-i*2,spiderY-8+i*3],[spiderX-22-i*2,spiderY+9+step]],'#3d363e',3);line([[spiderX+5,spiderY],[spiderX+13+i*2,spiderY-8+i*3],[spiderX+22+i*2,spiderY+9-step]],'#3d363e',3)}rect(spiderX-10,spiderY-7,21,12,'#332f3a');rect(spiderX-5,spiderY-11,12,9,'#45404a');rect(spiderX-4,spiderY-8,3,2,'#d35e55');rect(spiderX+2,spiderY-8,3,2,'#d35e55');
   // A bat flaps between pillars, with a small hanging colony farther back.
   const bx=542+Math.sin(t*.55)*32,by=281+Math.cos(t*1.2)*8,flap=Math.sin(t*8)*7;rect(bx-3,by-4,7,9,'#887066');line([[bx-3,by],[bx-12,by-3+flap],[bx-21,by+4+flap]],'#6e5b59',5);line([[bx+3,by],[bx+12,by-3+flap],[bx+21,by+4+flap]],'#6e5b59',5);rect(bx-4,by-6,2,3,'#ae8b70');rect(bx+3,by-6,2,3,'#ae8b70');
   // Miner works a diamond seam in the lower gallery.
   const mx=258,my=642;rect(mx-5,my-12,5,12,'#454052');rect(mx+3,my-12,5,12,'#393746');rect(mx-7,my-29,16,18,'#536e7a');rect(mx-6,my-42,14,13,'#b48a66');rect(mx-9,my-47,20,7,'#c5a24c');rect(mx+7,my-45,5,4,'#ffe8a2');const arm= Math.sin(t*2.6);line([[mx+7,my-26],[mx+18,my-27+arm*5],[mx+29,my-40+arm*9]],'#ad8662',5);line([[mx+19,my-46+arm*9],[mx+33,my-44+arm*9],[mx+39,my-37+arm*9]],'#91b2b1',4);
   // Skeleton and bow stand beside a supply chest at the far end.
   const sx=754,sy=642;rect(sx-5,sy-18,3,18,'#a7a99c');rect(sx+4,sy-18,3,18,'#9b9f96');rect(sx-5,sy-34,12,17,'#b6b6a5');for(let i=0;i<3;i++)rect(sx-5,sy-30+i*4,10,2,'#6e7880');rect(sx-7,sy-47,16,13,'#d4d0b9');rect(sx-5,sy-42,4,4,'#505962');rect(sx+2,sy-42,4,4,'#505962');line([[sx+5,sy-29],[sx+17,sy-25]],'#b6b6a5',3);line([[sx+17,sy-43],[sx+24,sy-30],[sx+17,sy-16]],'#92704b',3);line([[sx+17,sy-43],[sx+17,sy-16]],'#b6b3a1',1);
   beam(797,615,34,27);rect(811,623,5,7,'#e5c172');beam(192,325,29,22);beam(925,470,24,28);
   // Water seeps down the shaft and dust catches the warm torch light.
   ctx.globalAlpha=.4;rect(29,401,6,97,'#397a8c');for(let i=0;i<6;i++)rect(29,401+(i*17+t*23)%93,6,3,'#91c0bd');rect(20,510,55,3,'#649b9f');ctx.globalAlpha=1;
   for(let i=0;i<30;i++){const x=28+noise(i,32)*890+Math.sin(t*.3+i)*5,y=233+((noise(i,33)*405+t*(2+noise(i,34)*3))%405);ctx.globalAlpha=.12+noise(i,35)*.25;rect(x,y,2,2,'#e0caa1')}ctx.globalAlpha=1;
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

