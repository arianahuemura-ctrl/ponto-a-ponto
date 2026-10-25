// Deslocamento apenas visual, em pixels, à direita do sentido de circulação.
export function directedPath(points, offset=4, spacing=100) {
  points=points.filter((p,i)=>!i||p.x!==points[i-1].x||p.y!==points[i-1].y);
  const normals=points.slice(1).map((b,i)=>{
    const a=points[i],dx=b.x-a.x,dy=b.y-a.y,n=Math.hypot(dx,dy);
    return n?{x:-dy/n,y:dx/n}:{x:0,y:0};
  });
  const path=points.map((p,i)=>{
    const a=normals[Math.max(0,i-1)]||{x:0,y:0},b=normals[Math.min(i,normals.length-1)]||a;
    return {x:p.x+offset*(a.x+b.x)/2,y:p.y+offset*(a.y+b.y)/2};
  });
  const arrows=[];let next=spacing/2,total=0;
  for(let i=1;i<path.length;i++){
    const a=path[i-1],b=path[i],dx=b.x-a.x,dy=b.y-a.y,n=Math.hypot(dx,dy);
    if(!n)continue;
    while(next<=total+n){
      const t=(next-total)/n;
      arrows.push({x:a.x+t*dx,y:a.y+t*dy,angle:Math.atan2(dy,dx)*180/Math.PI});
      next+=spacing;
    }
    total+=n;
  }
  return {path,arrows};
}
