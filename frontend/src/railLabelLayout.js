// Screen-space layout, independent of Leaflet: keep text clear of tracks and markers.
export const labelBox=(point,width,height=30)=>({left:point.x-width/2,right:point.x+width/2,top:point.y-height/2,bottom:point.y+height/2});
export const overlaps=(a,b,gap=0)=>a.left<b.right+gap&&a.right>b.left-gap&&a.top<b.bottom+gap&&a.bottom>b.top-gap;
const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
function clip(a,b,box){
  let lo=0,hi=1;const dx=b.x-a.x,dy=b.y-a.y;
  for(const [p,q] of [[-dx,a.x-box.left],[dx,box.right-a.x],[-dy,a.y-box.top],[dy,box.bottom-a.y]]){
    if(p===0){if(q<0)return null;continue;}
    const t=q/p;
    if(p<0)lo=Math.max(lo,t);else hi=Math.min(hi,t);
    if(lo>hi)return null;
  }
  return [{x:a.x+lo*dx,y:a.y+lo*dy},{x:a.x+hi*dx,y:a.y+hi*dy}];
}
export const crossesBox=(a,b,box,padding=0)=>!!clip(a,b,{left:box.left-padding,right:box.right+padding,top:box.top-padding,bottom:box.bottom+padding});

export function placeRailLabels(lines,{width,height,obstacles=[]}){
  if(width<160||height<100)return [];
  const viewport={left:12,right:width-12,top:16,bottom:height-16};
  const center={x:width/2,y:height/2},segments=[];
  const choices=lines.map(line=>{
    const points=[];let length=0;
    for(const geometry of line.geometries)for(let i=1;i<geometry.length;i++){
      const segment=clip(geometry[i-1],geometry[i],viewport);
      if(!segment)continue;
      segments.push(segment);
      const [a,b]=segment,d=distance(a,b);
      if(d<1)continue;
      length+=d;const steps=Math.max(1,Math.ceil(d/80));
      for(let j=0;j<steps;j++){
        const f=(j+.5)/steps;
        points.push({x:a.x+(b.x-a.x)*f,y:a.y+(b.y-a.y)*f});
      }
    }
    return {line,length,points:points.sort((a,b)=>distance(a,center)-distance(b,center))};
  }).sort((a,b)=>a.length-b.length);
  const results=[],named=new Set();
  for(const {line,points} of choices){
    if(results.length>=32)break;
    // One name per viewport, also when the feed splits a line into branches.
    const key=line.label||line.route_id||line.code||line;
    if(named.has(key))continue;
    const labelHeight=line.height||30;
    if(line.width>width-24||labelHeight>height-32)continue;
    let chosen;
    for(const anchor of points){
      const offsets=[[0,-labelHeight/2-23],[0,labelHeight/2+23],[-line.width/2-18,0],[line.width/2+18,0],
        [0,-70],[0,70],[-line.width-35,-38],[line.width+35,38],
        [-line.width*2-35,-38],[line.width*2+35,38]];
      for(const [dx,dy] of offsets){
        const point={x:Math.max(viewport.left+line.width/2,Math.min(viewport.right-line.width/2,anchor.x+dx)),
          y:Math.max(viewport.top+labelHeight/2,Math.min(viewport.bottom-labelHeight/2,anchor.y+dy))};
        const box=labelBox(point,line.width,labelHeight);
        if(results.some(r=>overlaps(box,r.box,12))||obstacles.some(r=>overlaps(box,r,6)))continue;
        if(segments.some(([a,b])=>crossesBox(a,b,box,7)))continue;
        const vx=anchor.x-point.x,vy=anchor.y-point.y;
        const scale=Math.min(vx?line.width/2/Math.abs(vx):Infinity,vy?labelHeight/2/Math.abs(vy):Infinity);
        const edge={x:point.x+vx*scale,y:point.y+vy*scale};
        if(obstacles.some(r=>crossesBox(anchor,edge,r,3)))continue;
        chosen={line,anchor,point,edge,box};break;
      }
      if(chosen)break;
    }
    if(chosen){results.push(chosen);named.add(key);}
  }
  return results;
}
