import config from './elmina-map-config.json';
export const ELMINA_MAP_ID='elmina-lakeside-v1' as const;
export type GeoPoint={latitude:number;longitude:number};
export type ElminaMessage={type:'bioguard:map-ready'|'bioguard:map-point';map_id:typeof ELMINA_MAP_ID}&GeoPoint;
export type ElminaMapProps={mode?:'picker'|'view';initial?:GeoPoint|null;onPoint:(point:GeoPoint)=>void;onReady:()=>void;onError:(message:string)=>void};
export function isElminaPoint(value:unknown):value is GeoPoint{
 if(!value||typeof value!=='object')return false;const p=value as GeoPoint;const [southWest,northEast]=config.bounds;
 return Number.isFinite(p.latitude)&&Number.isFinite(p.longitude)&&p.latitude>=southWest[0]&&p.latitude<=northEast[0]&&p.longitude>=southWest[1]&&p.longitude<=northEast[1];
}
export function decodeMapMessage(value:unknown):ElminaMessage|null{
 if(!value||typeof value!=='object')return null;const p=value as ElminaMessage;
 return ['bioguard:map-ready','bioguard:map-point'].includes(p.type)&&p.map_id===ELMINA_MAP_ID&&isElminaPoint(p)?p:null;
}
export function elminaMapUrl(base:string,origin:string|undefined,mode:'picker'|'view',initial?:GeoPoint|null){
 const url=new URL(base.replace(/\/$/,'')+'/maps/elmina',origin);
 url.searchParams.set('mode',mode);if(origin)url.searchParams.set('parent_origin',new URL(origin).origin);
 if(isElminaPoint(initial)){url.searchParams.set('latitude',String(initial.latitude));url.searchParams.set('longitude',String(initial.longitude));}
 return url.href;
}
export function isElminaMapPage(candidate:string,expected:string){try{const a=new URL(candidate),b=new URL(expected);return a.origin===b.origin&&a.pathname===b.pathname;}catch{return false;}}
