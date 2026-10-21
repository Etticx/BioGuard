export const DEMO_MAP_ID = 'elmina-city-centre-v1' as const;
export const MAP_WIDTH = 642;
export const MAP_HEIGHT = 453;
export type Point = { x:number; y:number };
export type DemoPin = Point & { map_id:typeof DEMO_MAP_ID };
export type Size = { width:number; height:number };
export function isDemoPin(value:unknown):value is DemoPin {
 if(!value||typeof value!=='object')return false;
 const p=value as DemoPin;
 return p.map_id===DEMO_MAP_ID&&typeof p.x==='number'&&typeof p.y==='number'&&Number.isFinite(p.x)&&Number.isFinite(p.y)&&p.x>=0&&p.x<=1&&p.y>=0&&p.y<=1;
}
export function clampPoint(point:Point):Point {return {x:Math.max(0,Math.min(1,point.x)),y:Math.max(0,Math.min(1,point.y))};}
export function panPoint(point:Point,dx:number,dy:number,width:number,height:number):Point {
 if(width<=0||height<=0)return point;
 return clampPoint({x:point.x-dx/width,y:point.y-dy/height});
}
export function imageFrame(viewport:Size,point:Point,zoom:number){
 const scale=Math.min(viewport.width/MAP_WIDTH,viewport.height/MAP_HEIGHT)*zoom;
 const width=MAP_WIDTH*scale,height=MAP_HEIGHT*scale;
 return {width,height,left:viewport.width/2-point.x*width,top:viewport.height/2-point.y*height};
}
