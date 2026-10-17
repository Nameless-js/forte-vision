const clamp=(value:number)=>Math.min(1,Math.max(0,value));
export function mixColor(day:string,night:string,amount:number){
 const from=parseInt(day.slice(1),16),to=parseInt(night.slice(1),16),p=clamp(amount);
 const channel=(shift:number)=>Math.round(((from>>shift)&255)*(1-p)+((to>>shift)&255)*p);
 return `rgb(${channel(16)},${channel(8)},${channel(0)})`;
}

// Re-target from the current position, even during a rapid second click.
export function createDayCycle(initialNight:boolean){
 let from=initialNight?1:0,target=from,started=0,duration=0;
 const sample=(now:number)=>{const p=duration?clamp((now-started)/duration):1;return from+(target-from)*(p*p*(3-2*p))};
 return {sample,set(night:boolean,now:number,immediate=false){const next=night?1:0;if(next===target&&!immediate)return;from=sample(now);target=next;started=now;duration=immediate?0:4200*Math.abs(target-from)},get target(){return target}};
}

export function celestialPositions(nightAmount:number){
 const p=clamp(nightAmount);
 return {sun:{x:807+55*p,y:100+570*clamp(p/.75)},moon:{x:850-43*p,y:670-570*clamp((p-.25)/.75)}};
}
