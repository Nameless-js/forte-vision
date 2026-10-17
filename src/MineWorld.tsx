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
   // One continuous cavern: distant silhouettes, stepped rock and a foreground ledge.
   const poly=(points:number[][],color:string)=>{ctx.fillStyle=color;ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fill()};
   const rock=(x:number,y:number,w:number,h:number,seed:number,lit=false)=>{rect(x,y,w,h,lit?'#545650':'#3b4448');for(let yy=0;yy<h;yy+=16)for(let xx=0;xx<w;xx+=8){const n=noise(xx+seed*7,yy+seed*3);rect(x+xx,y+yy,Math.min(8,w-xx),Math.min(16,h-yy),n>.8?(lit?'#737369':'#545e60'):n>.45?(lit?'#5c605a':'#414c50'):(lit?'#4e544f':'#354046'));if(n>.7)rect(x+xx+1,y+yy+3,5,3,lit?'#8b887436':'#8a96902a');if(n<.17)rect(x+xx+2,y+yy+11,5,2,'#1c2b303b')}rect(x,y,w,3,lit?'#98967a':'#6e7b74');};
   const cave=ctx.createLinearGradient(0,170,0,690);cave.addColorStop(0,'#151f27');cave.addColorStop(.55,'#283b40');cave.addColorStop(1,'#14252e');ctx.fillStyle=cave;ctx.fillRect(0,170,960,520);
   // Larger, quieter shapes in the distance give the opening depth.
   for(let layer=0;layer<3;layer++)for(let x=0;x<960;x+=32){const n=noise(Math.floor(x/80),layer+20),top=200+layer*22+n*90,bottom=580-layer*35-n*45;rect(x,170,33,top-170,['#28343a','#253138','#1d2a32'][layer]);rect(x,bottom,33,700-bottom,['#243940','#293e42','#31484a'][layer]);if(n>.72)rect(x+8,top,14,35+n*40,'#26353b')}
   // A forgotten timber bridge spans a ravine in the far wall.
   ctx.globalAlpha=.55;for(const x of [383,454,525,596,667]){beam(x,334,6,130);beam(x-4,329,80,7);beam(x,401,6,88)}beam(375,398,370,8);for(let x=380;x<740;x+=13)rect(x,395,10,5,'#96724c');ctx.globalAlpha=1;
   for(let x=370;x<750;x+=32){rect(x,408,32,12,'#37484a');if(noise(x,14)>.4)rect(x,420,24,16,'#2b3b40')}
   rect(547,348,28,47,'#131f26');rect(551,354,20,39,'#1b2b31');
   // Blocky overhangs and stone shelves replace the regular gallery grid.
   for(let x=-24;x<984;x+=32){const edge=205+Math.floor(noise(Math.floor(x/64),41)*4)*24;rock(x,94,32,edge-94,x);if(noise(x,42)>.6)rock(x+8,edge,16,24,x+2)}
   for(let i=0;i<6;i++){const x=i*32,y=271+i*31;rock(x-25,y,54,380-y,i);rock(800+i*32,310-i*24,38,350,i+17)}
   // A broad foreground shore falls away into a blue-green underground pool.
   rect(0,573,960,120,'#16333c');for(let i=0;i<28;i++){const x=noise(i,68)*960,y=577+noise(i,69)*94;rect(x+Math.sin(t*.4+i)*5,y,12+noise(i,70)*43,2,i%3?'#2d5860':'#497075')}
   poly([[0,501],[95,501],[95,525],[190,525],[190,548],[313,548],[313,568],[440,568],[440,593],[566,593],[566,615],[960,615],[960,725],[0,725]],'#4b4e48');
   for(let x=0;x<960;x+=32){const floor=x<96?501:x<192?525:x<320?548:x<448?568:x<576?593:615;rock(x,floor,32,105,x+51,true)}
   // The nearer abandoned tunnel is built into the left cliff, with receding supports.
   rect(64,310,225,207,'#121b23');rect(95,333,163,177,'#182128');rect(129,354,105,150,'#1d272c');
   for(const [x,y,w,h]of [[77,317,195,207],[111,342,144,174],[143,365,94,147]]){beam(x,y,13,h);beam(x+w,y,13,h);beam(x-7,y-9,w+28,18);rect(x-5,y+h-5,23,6,'#b18b55')}
   // Rails bend out of the tunnel across the shelf, with visible sleepers.
   for(let i=0;i<25;i++){const p=i/24,x=185+p*600,y=489+p*151;line([[x-22,y+8],[x+15,y-9]],'#624a35',6)}
   line([[174,485],[288,530],[453,575],[785,628]],'#b5ad94',3);line([[205,476],[312,516],[476,560],[806,611]],'#939d96',3);
   // Cobwebs hang from timber corners rather than filling every opening.
   const web=(x:number,y:number,w:number,h:number)=>{ctx.globalAlpha=.38;for(let i=0;i<5;i++)line([[x,y],[x+w*(1-i/4),y+h*i/4]],'#c8c7b6',1);for(let i=1;i<5;i++){const p=i/4;line([[x+w*p,y],[x+w*p*.7,y+h*p*.3],[x+w*p*.3,y+h*p*.7],[x,y+h*p]],'#c8c7b6',1)}ctx.globalAlpha=1};web(91,325,58,62);web(785,275,54,66);web(599,340,27,30);
   // Torches illuminate the stone with warm pools of light and pixel sparks.
   const torch=(x:number,y:number,scale=1)=>{const glow=ctx.createRadialGradient(x,y,1,x,y,100*scale);glow.addColorStop(0,'#ffbe6550');glow.addColorStop(.5,'#db85351c');glow.addColorStop(1,'#db853500');ctx.fillStyle=glow;ctx.fillRect(x-100*scale,y-100*scale,200*scale,200*scale);rect(x,y+2,4*scale,17*scale,'#99703e');rect(x-2*scale,y-8*scale,8*scale,12*scale,'#d77c29');rect(x,y-11*scale+Math.sin(t*9+x)*2,4*scale,14*scale,'#ffe69c');for(let i=0;i<3;i++){ctx.globalAlpha=.6;rect(x+Math.sin(i+t)*5,y-10-((t*17+i*11)%25),2,2,'#ffc76e')}ctx.globalAlpha=1};torch(100,406);torch(276,448);torch(784,419);torch(457,373,.45);
   // Ore uses the familiar clustered pixels embedded in individual stone blocks.
   for(const [x,y,color]of [[37,377,'#bc906b'],[304,528,'#cba44f'],[865,349,'#72c7bd'],[889,382,'#67c0c0'],[73,554,'#be7657']] as const){for(let i=0;i<8;i++){const xx=x+Math.floor(noise(i,x)*5)*5,yy=y+Math.floor(noise(i,y)*5)*5;rect(xx,yy,5,4,color);rect(xx,yy,2,2,'#dbe5c88a')}}
   // Minecart: top rim, side face, shaded end and iron wheels.
   const cx=360+Math.sin(t*.19)*13,cy=540+Math.sin(t*.19)*3;poly([[cx-23,cy-25],[cx+11,cy-33],[cx+31,cy-23],[cx-4,cy-15]],'#a3a59c');poly([[cx-23,cy-25],[cx-4,cy-15],[cx-4,cy+6],[cx-20,cy-1]],'#515e62');poly([[cx-4,cy-15],[cx+31,cy-23],[cx+27,cy-1],[cx-4,cy+6]],'#7e8987');rect(cx-2,cy-12,26,3,'#b0b3a6');for(const x of [cx-13,cx+18]){rect(x-4,cy+1,8,9,'#202c33');rect(x-2,cy+3,4,4,'#8c9895')}
   // A creeper half hidden behind the far rock; a bat circles over the ravine.
   const crx=713,cry=615;rect(crx-7,cry-9,6,9,'#3b5a48');rect(crx+4,cry-9,6,9,'#304f40');rect(crx-5,cry-29,13,22,'#567951');rect(crx-9,cry-46,20,18,'#6e9159');rect(crx-9,cry-46,20,4,'#86a265');rect(crx-6,cry-40,4,4,'#1b332c');rect(crx+3,cry-40,4,4,'#1b332c');rect(crx-2,cry-36,5,6,'#1b332c');rect(crx-5,cry-32,4,5,'#1b332c');rect(crx+2,cry-32,4,5,'#1b332c');
   const bx=590+Math.sin(t*.4)*55,by=298+Math.cos(t*.9)*13,flap=Math.sin(t*7)*8;rect(bx-3,by-4,7,9,'#7d7369');line([[bx-3,by],[bx-13,by-4+flap],[bx-22,by+4+flap]],'#635d5c',4);line([[bx+3,by],[bx+13,by-4+flap],[bx+22,by+4+flap]],'#635d5c',4);
   // Foreground boulders frame the view, plus moss, mushrooms and an old chest.
   rock(0,620,79,92,83,true);rock(45,650,90,80,86);rock(850,532,53,150,80);rock(902,485,58,218,84);rock(826,578,36,100,87);
   for(const [x,y]of [[28,620],[62,650],[858,532],[911,485]]){rect(x,y,23,4,'#526a4d');rect(x+3,y+4,5,9,'#415846')}
   for(const [x,y]of [[746,603],[807,615],[122,559]]){rect(x,y-9,3,11,'#c3b58d');rect(x-5,y-12,14,5,'#a96448');rect(x-2,y-15,8,4,'#bf8060');rect(x-2,y-12,3,2,'#e0c49c')}
   beam(610,590,35,25);rect(610,598,35,3,'#3a2b24');rect(625,598,5,7,'#d7ba72');
   for(let i=0;i<35;i++){const x=noise(i,32)*960+Math.sin(t*.3+i)*7,y=240+((noise(i,33)*400+t*(2+noise(i,34)*3))%400);ctx.globalAlpha=.1+noise(i,35)*.2;rect(x,y,2,2,'#d9c697')}ctx.globalAlpha=1;
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

