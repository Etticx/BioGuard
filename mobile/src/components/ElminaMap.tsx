import {useEffect,useRef} from 'react';
import {base} from '../services/reports';
import {decodeMapMessage,elminaMapUrl,ELMINA_MAP_ID,type ElminaMapProps} from '../services/elminaMap';
export function ElminaMap({initial,onPoint,onReady,onError,mode='picker'}:ElminaMapProps){
 const frame=useRef<HTMLIFrameElement>(null);const url=elminaMapUrl(base,window.location.origin,mode,initial);
 useEffect(()=>{
  let ready=false;const timer=setTimeout(()=>{if(!ready)onError('The map could not load. Check your connection and retry.');},25000);
  const receive=(event:MessageEvent)=>{
   if(event.origin!==new URL(url).origin||event.source!==frame.current?.contentWindow)return;
   const message=decodeMapMessage(event.data);
   if(message){onPoint({latitude:message.latitude,longitude:message.longitude});if(message.type==='bioguard:map-ready'){ready=true;clearTimeout(timer);onReady();}}
   else if(event.data?.type==='bioguard:map-error'&&event.data?.map_id===ELMINA_MAP_ID)onError('The map could not load. Check your connection and retry.');
  };
  window.addEventListener('message',receive);return()=>{clearTimeout(timer);window.removeEventListener('message',receive);};
 },[url,onPoint,onReady,onError]);
 return <iframe ref={frame} title="Elmina Lakeside plant location map" src={url} referrerPolicy="strict-origin-when-cross-origin" style={{width:'100%',height:'100%',border:0,display:'block'}} onError={()=>onError('Could not open the map. Check your backend connection.')}/>;
}
