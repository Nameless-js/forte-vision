import {useEffect,useRef} from 'react';

// A real-time, deliberately low-resolution world. All art is drawn locally.
export function World({night,animated}:{night:boolean;animated:boolean}){
 const ref=useRef<HTMLCanvasElement>(null);
 useEffect(()=>{
  const canvas=ref.current!,ctx=canvas.getContext('2d')!;
  canvas.width=960;canvas.height=600;ctx.imageSmoothingEnabled=false;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  let frame=0,last=0;const start=performance.now();let pointerX=0,pointerY=0;
  const mouse=(e:PointerEvent)=>{pointerX=(e.clientX/innerWidth-.5)*8;pointerY=(e.clientY/innerHeight-.5)*4};
  window.addEventListener('pointermove',mouse,{passive:true});
  const noise=(a:number,b:number)=>{const n=Math.sin(a*127.1+b*311.7)*43758.5453;return n-Math.floor(n)};
  const rect=(x:number,y:number,w:number,h:number,color:string)=>{ctx.fillStyle=color;ctx.fillRect(Math.round(x),Math.round(y),w,h)};
  const poly=(points:number[][],color:string)=>{ctx.fillStyle=color;ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(Math.round(x),Math.round(y)):ctx.moveTo(Math.round(x),Math.round(y)));ctx.closePath();ctx.fill()};
  const block=(x:number,y:number,s:number,top:string,front:string,side:string)=>{poly([[x,y],[x+s,y-s/2],[x+s*2,y],[x+s,y+s/2]],top);poly([[x,y],[x+s,y+s/2],[x+s,y+s*1.5],[x,y+s]],front);poly([[x+s,y+s/2],[x+s*2,y],[x+s*2,y+s],[x+s,y+s*1.5]],side)};
  const tree=(x:number,y:number,s:number,birch=false)=>{
   rect(x-4*s,y-45*s,9*s,48*s,birch?'#a0afa0':'#59432c');rect(x+2*s,y-44*s,3*s,48*s,birch?'#687972':'#362f23');
   if(birch)for(let i=0;i<5;i++)rect(x-3*s,y-43*s+i*9*s,4*s,2*s,'#384c48');
   const colors=night?['#24483b','#2e5b3e','#396b41']:['#315c3c','#487c43','#5b924a'];
   for(let i=0;i<3;i++){const w=(56-i*12)*s,yy=y-63*s-i*18*s;rect(x-w/2,yy,w,25*s,colors[i]);rect(x-w/2,yy+18*s,w,7*s,'#244838');for(let j=0;j<13;j++)rect(x-w/2+noise(j,i+x)*w,yy+noise(j+33,i+y)*18*s,4*s,3*s,j%2?'#79a25050':'#133a3060')}
  };
  const house=(x:number,y:number,s:number,t:number)=>{
   rect(x,y-65*s,80*s,65*s,'#84724e');rect(x+6*s,y-58*s,68*s,58*s,'#b39b68');
   for(let i=0;i<8;i++){rect(x+6*s,y-57*s+i*7*s,68*s,2*s,'#817049');rect(x+(i%2?25:45)*s,y-55*s+i*7*s,2*s,5*s,'#8e774c')}
   rect(x,y-65*s,8*s,65*s,'#4c4430');rect(x+72*s,y-65*s,8*s,65*s,'#4c4430');
   for(let i=0;i<6;i++)rect(x-12*s+i*8*s,y-65*s-i*8*s,(104-i*16)*s,9*s,i%2?'#554231':'#65503a');
   rect(x+29*s,y-30*s,22*s,30*s,'#3b3c2c');rect(x+32*s,y-27*s,16*s,27*s,'#685233');rect(x+44*s,y-15*s,3*s,3*s,'#e0c16b');
   for(const xx of [12,56]){rect(x+xx*s,y-45*s,14*s,16*s,'#3b4334');rect(x+(xx+2)*s,y-43*s,10*s,12*s,'#e6bc63');rect(x+(xx+6)*s,y-43*s,2*s,12*s,'#89693d');rect(x+(xx+2)*s,y-38*s,10*s,2*s,'#89693d')}
   rect(x+56*s,y-111*s,12*s,26*s,'#72776b');rect(x+54*s,y-113*s,16*s,5*s,'#909083');
   for(let i=0;i<5;i++){const p=(t*.35+i*.2)%1;ctx.globalAlpha=(1-p)*.35;rect(x+57*s+Math.sin(p*7)*8*s,y-117*s-p*68*s,(5+p*12)*s,(5+p*12)*s,'#c4d2b8');ctx.globalAlpha=1}
  };
  const draw=(now:number)=>{
   if(now-last<40&&animated&&!reduced){frame=requestAnimationFrame(draw);return}last=now;
   const t=animated&&!reduced?(now-start)/1000:0;
   const sky=ctx.createLinearGradient(0,0,0,600);sky.addColorStop(0,night?'#071c27':'#26464b');sky.addColorStop(.5,night?'#183f46':'#678e79');sky.addColorStop(.78,night?'#315b50':'#cfb276');sky.addColorStop(1,'#294e3c');ctx.fillStyle=sky;ctx.fillRect(0,0,960,600);
   // Stars and drifting, stepped clouds cover the entire world.
   for(let i=0;i<110;i++){let x=noise(i,2)*960,y=noise(i,3)*340;ctx.globalAlpha=(night?.8:.3)*(.45+Math.sin(t*.7+i)*.4);rect(x,y,i%13===0?3:1,i%13===0?3:1,'#e6f0bb')};ctx.globalAlpha=1;
   const sx=807+pointerX*.4,sy=100+pointerY*.4;rect(sx-7,sy-7,68,68,night?'#a5dbb815':'#ffd88f0c');rect(sx,sy,54,54,night?'#d5e5bf':'#f3d28a');rect(sx+8,sy+7,38,38,night?'#e9f0cb':'#ffe8a8');if(night){rect(sx+8,sy+12,8,7,'#afc8a6');rect(sx+29,sy+31,10,9,'#afc8a6')}
   for(let i=0;i<7;i++){const x=((i*173+t*(2+i%3))%1150)-100+pointerX*.5,y=48+(i%4)*52;ctx.globalAlpha=night?.13:.23;rect(x,y,98,12,'#d6e6bd');rect(x+18,y-11,46,11,'#d6e6bd');rect(x+8,y+12,77,4,'#9fb8a3');ctx.globalAlpha=1}
   // Far mountains are continuous stepped silhouettes, never a framed image.
   for(let layer=0;layer<3;layer++){const base=350+layer*48;ctx.fillStyle=['#335b58','#294e43','#203f32'][layer];for(let x=-20;x<980;x+=12){const h=50+Math.sin(x/(130-layer*20)+layer)*36+Math.sin(x/55+layer)*22;ctx.fillRect(x+pointerX*(layer+1)/3,base-h+pointerY,13,600-base+h)}}
   for(let i=0;i<27;i++){const x=i*41+noise(i,7)*24;tree(x,391+Math.sin(i)*18,.37+noise(i,9)*.25)}
   // Ground and stream, with individual dirt and stone pixels.
   poly([[0,488],[96,488],[96,476],[210,476],[210,492],[353,492],[353,479],[480,479],[480,442],[554,442],[554,426],[701,426],[701,438],[843,438],[843,416],[960,416],[960,600],[0,600]],'#31532e');
   for(let x=0;x<960;x+=16){let y=x<450?496:450;rect(x,y,16,150,'#473c2c');for(let j=0;j<9;j++){rect(x+noise(x,j)*12,y+6+j*16,5,4,noise(x+1,j)>.5?'#5b4b32':'#332f26')}rect(x,y-8,16,9,x%3?'#5e7b38':'#6c8940');rect(x,y+1,5,5,'#4b682f')}
   poly([[676,430],[712,430],[701,463],[659,488],[675,513],[735,551],[760,600],[652,600],[632,555],[596,518],[604,481],[655,453]],night?'#276e75':'#4e9b99');
   for(let i=0;i<28;i++){const yy=441+i*6,xx=675+Math.sin(i*.28)*40+(i>14?(i-14)*3:0);ctx.globalAlpha=.25+Math.sin(t*2+i)*.18;rect(xx+Math.sin(t+i)*5,yy,10+noise(i,8)*15,2,'#b2e4bd')};ctx.globalAlpha=1;
   // The village lives on the right, leaving a calm sky behind the copy.
   house(720,419,.95,t);house(859,429,.62,t+.5);tree(900,435,1.05);tree(546,460,.85,true);tree(496,463,1.1);tree(805,474,.67,true);
   // Blocky watchtower and a rotating scanner above it.
   rect(620,337,39,100,'#778477');rect(625,340,5,94,'#93a18a');for(let i=0;i<7;i++)rect(630+(i%2)*9,341+i*13,19,2,'#536b60');
   rect(615,329,49,11,'#3b5148');rect(616,320,8,14,'#91a18a');rect(634,320,8,14,'#91a18a');rect(653,320,10,14,'#91a18a');rect(632,353,15,20,'#233f34');rect(635,356,9,13,'#edce79');
   rect(639,271,3,49,'#8da78b');rect(634,269,13,11,'#b6edbb');ctx.globalAlpha=.09;poly([[641,273],[641+Math.cos(t*.6)*180,200],[641+Math.cos(t*.6)*180,410]],'#b9efb4');ctx.globalAlpha=1;
   // Fence, wheat and lanterns.
   for(let i=0;i<12;i++){const x=746+i*10;rect(x,453,3,19,'#8f7950');rect(x-7,459,10,3,'#ad9765')}
   for(let i=0;i<28;i++){const x=849+noise(i,4)*72,y=477+noise(i,5)*35;rect(x,y-10,2,13,'#b4a94f');rect(x-2,y-13,6,6,i%2?'#d5bd62':'#b19d48')}
   const torch=(x:number,y:number)=>{const glow=ctx.createRadialGradient(x,y,1,x,y,32);glow.addColorStop(0,'#ffd37640');glow.addColorStop(1,'#ffd37600');ctx.fillStyle=glow;ctx.fillRect(x-32,y-32,64,64);rect(x-1,y,3,15,'#8a6838');rect(x-3,y-7,7,9,'#f3b94f');rect(x-1,y-9+(Math.floor(t*6)%2)*2,3,7,'#fff0a4')};torch(703,450);torch(833,445);torch(595,471);
   // Campfire flames, smoke and explorer's arm motion.
   rect(744,509,22,4,'#3c3024');poly([[745,508],[749,494-Math.sin(t*8)*3],[754,500],[760,490],[764,508]],'#d98635');poly([[751,508],[755,496],[760,508]],'#ffe598');
   for(let i=0;i<5;i++){const p=(t*.25+i*.2)%1;ctx.globalAlpha=(1-p)*.4;rect(753+Math.sin(p*7)*9,488-p*56,3+p*7,3+p*7,'#b7bda5');ctx.globalAlpha=1}
   const walk=Math.sin(t*2)*2;rect(710,492,7,19,'#334c72');rect(721,492,7,19,'#283b5c');rect(709,472,20,21,'#4d9c9b');rect(710,458,16,15,'#b78a61');rect(708,456,19,6,'#45392c');rect(723,465,3,2,'#263e3a');rect(727,475+walk,6,16,'#b78a61');
   // Sheep wanders, looks around and bobs its head.
   const sheepX=831+Math.sin(t*.13)*34,step=Math.floor(t*3)%2;rect(sheepX,523,6,9+step,'#493e31');rect(sheepX+20,523,6,10-step,'#493e31');rect(sheepX-3,507,34,18,'#d5d9be');rect(sheepX,504,25,6,'#eef0d2');rect(sheepX+24,510+step,13,13,'#aaa88d');rect(sheepX+33,513+step,2,2,'#29392d');
   // Foreground grass, flowers, fireflies. Stable random positions.
   for(let i=0;i<80;i++){const x=noise(i,12)*960,y=531+noise(i,13)*69;if(x>600&&x<755)continue;rect(x,y,2,7,'#5b7636');rect(x-3,y-3,3,5,'#486530');if(i%5===0)rect(x-2,y-5,6,4,i%2?'#d6b45c':'#cda18b')}
   for(let i=0;i<33;i++){const x=40+noise(i,20)*880+Math.sin(t*.4+i)*13,y=185+noise(i,21)*375+Math.cos(t*.6+i)*9;ctx.globalAlpha=(.4+Math.sin(t*1.3+i)*.35)*(night?1:.6);rect(x,y,i%7===0?3:2,i%7===0?3:2,i%3?'#c2e889':'#ffe29c')};ctx.globalAlpha=1;
   // Occasional birds cross the sky.
   for(let i=0;i<3;i++){const x=(t*11+i*74+520)%1100-40,y=158+Math.sin(t*.3+i)*12+i*11;rect(x,y,3,2,'#162e2c');rect(x-3,y-(Math.floor(t*5)%2?2:0),3,2,'#162e2c');rect(x+3,y-(Math.floor(t*5)%2?2:0),3,2,'#162e2c')}
   // Vignette anchors copy while keeping sky visible throughout.
   const shade=ctx.createLinearGradient(0,0,960,0);shade.addColorStop(0,'#081d24c9');shade.addColorStop(.47,'#0a222d75');shade.addColorStop(.72,'#10292b00');ctx.fillStyle=shade;ctx.fillRect(0,0,960,600);
   if(animated&&!reduced)frame=requestAnimationFrame(draw);
  };
  draw(performance.now());
  return()=>{cancelAnimationFrame(frame);window.removeEventListener('pointermove',mouse)};
 },[night,animated]);
 return <canvas className="world-canvas" ref={ref} aria-label="Живой пиксельный Overworld: деревня, лес, река, овца, костёр и башня наблюдения"/>;
}

export function PixelItem({kind}:{kind:'grass'|'diamond'|'chest'|'torch'|'sword'|'book'|'compass'|'pickaxe'|'eye'}){
 const paths:Record<string,string>={
  grass:'M2 5h12v9H2z',diamond:'M5 2h6l4 5-7 8L1 7z',chest:'M2 5h12v9H2zM2 4h12v3H2z',torch:'M6 6h4v9H6zM5 2h6v5H5z',sword:'M11 1h4v4l-7 7-4-4zM2 10l4 4M1 15l4-4',book:'M3 2h10v13H3zM5 2v13',compass:'M8 1l7 7-7 7-7-7zM10 5L8 9 6 11l2-5z',pickaxe:'M3 2h8l4 4-2 2-4-3H3zM8 5L2 14',eye:'M1 6l4-3h6l4 3v5l-4 3H5l-4-3zM6 5h4v6H6z'};
 return <svg className={`pixel-item item-${kind}`} viewBox="0 0 16 16" shapeRendering="crispEdges" aria-hidden="true"><path d={paths[kind]} fill={kind==='sword'||kind==='pickaxe'?'none':'currentColor'} stroke="currentColor" strokeWidth="1.6"/>{kind==='grass'&&<path d="M2 4h12v4H2z" fill="#82bf49"/>}{kind==='chest'&&<path d="M7 7h2v4H7z" fill="#ffe28b"/>}</svg>
}
