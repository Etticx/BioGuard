/* Geographic selection only: these blocks do not predict infestation or spread. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.BioGuardBlocks=api;})(typeof window!=='undefined'?window:this,function(){
 'use strict';
 const EPS=1e-10;
 function ringState(ring,p){
  let inside=false;
  for(let i=0,j=ring.length-1;i<ring.length;j=i++){
   const a=ring[j],b=ring[i],dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy);
   if(len>0){const cross=(p[0]-a[0])*dy-(p[1]-a[1])*dx;
    if(Math.abs(cross)<=EPS*len&&p[0]>=Math.min(a[0],b[0])-EPS&&p[0]<=Math.max(a[0],b[0])+EPS&&p[1]>=Math.min(a[1],b[1])-EPS&&p[1]<=Math.max(a[1],b[1])+EPS)return 2;}
   if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside;
  }return inside?1:0;
 }
 function polygonState(rings,p){const exterior=ringState(rings[0],p);if(!exterior)return 0;for(const hole of rings.slice(1)){const h=ringState(hole,p);if(h===1)return 0;if(h===2)return 2;}return exterior;}
 function state(feature,p){const g=feature.geometry;if(g?.type==='Polygon')return polygonState(g.coordinates,p);if(g?.type==='MultiPolygon')return Math.max(0,...g.coordinates.map(r=>polygonState(r,p)));return 0;}
 function classify(data,p){
  if(!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite))return{kind:'unmapped',features:[]};
  const all=Array.isArray(data?.features)?data.features:[];
  const water=all.filter(f=>f.properties?.type==='water'&&state(f,p));
  if(water.length)return{kind:'water',features:water};
  const blocks=all.filter(f=>f.properties?.type==='inspection_block'&&state(f,p)).sort((a,b)=>String(a.properties.block_id).localeCompare(String(b.properties.block_id)));
  return{kind:blocks.length>1?'boundary':blocks.length===1?'block':'unmapped',features:blocks};
 }
 return{classify};
});
