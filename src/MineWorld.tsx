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
   // A quiet side-view mining scene at the same small sprite scale as the Overworld.
   const rock=(x:number,y:number,w:number,h:number,seed:number)=>{rect(x,y,w,h,'#3e4548');for(let yy=0;yy<h;yy+=12)for(let xx=0;xx<w;xx+=12){const n=noise(xx+seed,yy+seed*3);rect(x+xx,y+yy,Math.min(12,w-xx),Math.min(12,h-yy),n>.72?'#505759':n>.36?'#41494b':'#353e42');if(n>.8)rect(x+xx+2,y+yy+3,6,2,'#69716c55')}rect(x,y,w,2,'#747b6b')};
   const back=ctx.createLinearGradient(0,180,0,680);back.addColorStop(0,'#18262d');back.addColorStop(.6,'#253b40');back.addColorStop(1,'#1c3037');ctx.fillStyle=back;ctx.fillRect(0,180,960,510);
   // Distant cave silhouettes remain understated behind the small foreground details.
   for(let layer=0;layer<3;layer++)for(let x=0;x<960;x+=16){const n=noise(Math.floor(x/48),layer+20),top=211+layer*19+n*44,bottom=530+layer*33-n*36;rect(x,180,17,top-180,['#29373d','#26353b','#223139'][layer]);rect(x,bottom,17,690-bottom,['#2c4247','#30464a','#33474a'][layer]);if(n>.8)rect(x+3,top,7,20,'#26383d')}
   // Fine stone blocks carve an irregular roof; the central view stays open.
   for(let x=0;x<960;x+=16){const edge=207+Math.floor(noise(Math.floor(x/48),41)*3)*16;rock(x,94,16,edge-94,x)}
   for(let x=0;x<960;x+=16){const left=x<160, right=x>816;if(left||right){const top=left?350+Math.floor(x/32)*16:350+Math.floor((960-x)/32)*16;rock(x,top,16,690-top,x+2)}}
   // Three low natural shelves rather than giant tunnel frames.
   for(let x=64;x<367;x+=16)rock(x,449+(x>304?16:0),16,33,x+14);
   for(let x=544;x<896;x+=16)rock(x,419+(x<608?16:0),16,33,x+18);
   for(let x=0;x<960;x+=16){const y=598+Math.floor(noise(Math.floor(x/80),5)*3)*16;rock(x,y,16,100,x+31)}
   // A modest working tunnel tucked into the left shelf.
   rect(98,366,107,83,'#16252c');rect(111,376,82,73,'#1c2d33');
   for(const x of [107,184]){beam(x,369,6,80)}beam(102,363,96,8);
   // Small timber supports on the far shelf match the houses and sprites above ground.
   for(const x of [605,701,797]){beam(x,361,5,58);beam(x+61,361,5,58);beam(x-3,356,72,7)}
   const torch=(x:number,y:number)=>{const glow=ctx.createRadialGradient(x,y,1,x,y,43);glow.addColorStop(0,'#ffc36c38');glow.addColorStop(1,'#ffc36c00');ctx.fillStyle=glow;ctx.fillRect(x-43,y-43,86,86);rect(x,y+2,2,8,'#9e7b4d');rect(x-1,y-4,4,7,'#dc8c36');rect(x,y-6+Math.sin(t*8+x),2,7,'#ffe9a6')};
   for(const [x,y]of [[113,395],[333,430],[615,383],[806,384],[463,570],[865,579]])torch(x,y);
   // Rails, a small cart and a supply chest on the working shelf.
   for(let x=111;x<350;x+=12)rect(x,445,7,3,'#91714a');rect(111,443,241,2,'#a4a79b');rect(111,448,241,1,'#697b7d');
   const cart=260+Math.sin(t*.22)*16;rect(cart,432,23,12,'#778587');rect(cart-2,430,27,3,'#a7afa4');rect(cart+3,442,5,5,'#28343b');rect(cart+17,442,5,5,'#28343b');rect(cart+3,432,17,3,'#9aa5a1');
   beam(756,403,19,16);rect(756,408,19,2,'#3f3028');rect(764,408,3,5,'#d8bc75');
   // Familiar ore clusters are small, occasional accents in the rock.
   for(const [x,y,color]of [[43,401,'#bd9470'],[231,456,'#c2a65e'],[829,472,'#6dafb5'],[676,625,'#9f7761'],[350,622,'#7fbab4'],[93,487,'#bd9470'],[268,470,'#c2a65e'],[628,438,'#65bec0'],[861,525,'#68b8bd'],[184,616,'#b95e54'],[743,641,'#c8aa64'],[907,376,'#b98d69'],[387,204,'#939d96']] as const)for(let i=0;i<5;i++){const xx=x+Math.floor(noise(i,x)*4)*4,yy=y+Math.floor(noise(i,y)*3)*4;rect(xx,yy,4,3,color);rect(xx,yy,1,1,'#d4e2cc')}
   // Third-person miner: compact full-body sprite with an animated pickaxe.
   const px=309,py=449;rect(px-4,py-9,3,9,'#3f4866');rect(px+2,py-9,3,9,'#36415c');rect(px-5,py-21,11,13,'#49858b');rect(px-5,py-30,11,10,'#b9906d');rect(px-6,py-32,13,4,'#5c4438');rect(px+3,py-27,2,2,'#293d40');const swing=Math.sin(t*2.5)*4;line([[px+5,py-17],[px+12,py-15],[px+19,py-25+swing]],'#b59070',3);line([[px+14,py-29+swing],[px+23,py-27+swing],[px+26,py-23+swing]],'#9db6b2',2);
   // A second tiny miner works in the distance, keeping the scene inhabited and calm.
   rect(648,410,3,9,'#46566b');rect(654,410,3,9,'#3a495d');rect(647,400,11,11,'#61837a');rect(648,392,9,8,'#b18e71');rect(646,390,13,3,'#b9a15a');
   // A narrow underground stream, gentle droplets and a bat far above.
   rect(373,589,157,8,'#365f65');for(let i=0;i<9;i++)rect(377+i*17+Math.sin(t+i)*3,592,7,1,'#7a9c97');ctx.globalAlpha=.45;rect(503,241,3,327,'#46767d');for(let i=0;i<12;i++)rect(503,246+(i*27+t*20)%315,3,3,'#92b4ab');ctx.globalAlpha=1;
   const bx=465+Math.sin(t*.35)*22,by=320+Math.cos(t*.7)*6,f=Math.sin(t*7)*3;rect(bx,by,4,5,'#7d776a');line([[bx,by+1],[bx-6,by-2+f],[bx-10,by+2+f]],'#68675f',2);line([[bx+4,by+1],[bx+10,by-2+f],[bx+14,by+2+f]],'#68675f',2);
   for(let i=0;i<20;i++){const x=noise(i,32)*960+Math.sin(t*.3+i)*4,y=270+((noise(i,33)*315+t*2)%315);ctx.globalAlpha=.1+noise(i,35)*.15;rect(x,y,1,1,'#d9c697')}ctx.globalAlpha=1;
   // A small lava pocket in the lower stone, separated from the stream.
   const lavaGlow=ctx.createRadialGradient(747,607,3,747,607,67);lavaGlow.addColorStop(0,'#ff9f453b');lavaGlow.addColorStop(1,'#ff9f4500');ctx.fillStyle=lavaGlow;ctx.fillRect(680,540,134,134);
   rect(703,611,92,8,'#a34a29');rect(709,608,80,6,'#ec7e32');rect(720,605,56,4,'#f6a848');
   for(let i=0;i<8;i++){const x=712+i*9+Math.sin(t*.6+i)*2;rect(x,610+(i%2)*3,5,1,Math.sin(t*1.7+i)>.2?'#ffd680':'#c85e29')}
   for(let i=0;i<4;i++){const y=605-((t*9+i*12)%35);ctx.globalAlpha=(y-570)/50;rect(724+i*14+Math.sin(t+i)*3,y,1,2,'#ffb365')}ctx.globalAlpha=1;
   // Tiny mobs share the existing shelves without changing the cave layout.
   const zx=156+Math.sin(t*.24)*9,zy=449,step=Math.sin(t*3)*1.2;
   rect(zx-4,zy-8,3,8+step,'#3f4661');rect(zx+2,zy-8,3,8-step,'#353c57');rect(zx-5,zy-20,11,13,'#3e777b');rect(zx+5,zy-18,8,3,'#7c985a');rect(zx-5,zy-30,11,10,'#78965b');rect(zx-5,zy-30,11,3,'#526e46');rect(zx+2,zy-25,2,2,'#233f32');
   const kx=841,ky=419;rect(kx-5,ky-6,4,6,'#3d5b3e');rect(kx+2,ky-6,4,6,'#34513a');rect(kx-3,ky-19,7,14,'#698650');rect(kx-6,ky-29,13,11,'#83a165');rect(kx-4,ky-25,3,3,'#263d2b');rect(kx+2,ky-25,3,3,'#263d2b');rect(kx-1,ky-22,3,4,'#263d2b');rect(kx-3,ky-20,2,3,'#263d2b');rect(kx+2,ky-20,2,3,'#263d2b');
   const spiderX=584+Math.sin(t*.34)*10,spiderY=435;
   for(let i=0;i<3;i++){const d=Math.sin(t*4+i);line([[spiderX-3,spiderY-3],[spiderX-8-i*2,spiderY-6],[spiderX-12-i,spiderY+d]],'#45434a',1);line([[spiderX+3,spiderY-3],[spiderX+8+i*2,spiderY-6],[spiderX+12+i,spiderY-d]],'#45434a',1)}rect(spiderX-5,spiderY-6,10,5,'#37383f');rect(spiderX-3,spiderY-7,6,4,'#4b454a');rect(spiderX-2,spiderY-6,1,1,'#bd6960');rect(spiderX+1,spiderY-6,1,1,'#bd6960');
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
export function MineIntro(){const {t}=useI18n();return <section className="mine-descent" aria-label={t('Шахта')}><div className="mine-sign"><span>{t('НИЖЕ ПОВЕРХНОСТИ')}</span><h2>{t('Шахта')}</h2><p>{t('Самое важное часто скрыто глубже.')}</p></div><div className="mine-depth"><span>↓</span>{t('ГЛУБИНА: 32 БЛОКА')}</div></section>}

