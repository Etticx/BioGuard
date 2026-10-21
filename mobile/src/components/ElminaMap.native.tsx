import {useEffect,useRef} from 'react';
import {Linking,StyleSheet} from 'react-native';
import {WebView} from 'react-native-webview';
import {base} from '../services/reports';
import {decodeMapMessage,elminaMapUrl,isElminaMapPage,ELMINA_MAP_ID,type ElminaMapProps} from '../services/elminaMap';
export function ElminaMap({initial,onPoint,onReady,onError}:ElminaMapProps){
 const url=elminaMapUrl(base,undefined,'picker',initial);const ready=useRef(false);
 useEffect(()=>{const timer=setTimeout(()=>{if(!ready.current)onError('The map could not load. Check your connection and retry.');},25000);return()=>clearTimeout(timer);},[onError]);
 return <WebView source={{uri:url}} style={styles.map} applicationNameForUserAgent="BioGuard/0.2" originWhitelist={['http://*','https://*']} javaScriptEnabled scrollEnabled={false} bounces={false}
  onShouldStartLoadWithRequest={request=>{
   if(isElminaMapPage(request.url,url))return true;
   if(['https://www.openstreetmap.org/copyright','https://leafletjs.com','https://leafletjs.com/'].includes(request.url))void Linking.openURL(request.url);
   return false;
  }}
  onMessage={event=>{
   if(!isElminaMapPage(event.nativeEvent.url,url))return;
   try{const value=JSON.parse(event.nativeEvent.data);const message=decodeMapMessage(value);
    if(message){onPoint({latitude:message.latitude,longitude:message.longitude});if(message.type==='bioguard:map-ready'){ready.current=true;onReady();}}
    else if(value?.type==='bioguard:map-error'&&value?.map_id===ELMINA_MAP_ID)onError('The map could not load. Check your connection and retry.');
   }catch{/* Ignore unrecognised messages. */}
  }} onError={()=>onError('Could not open the map. Check your backend connection.')} onHttpError={()=>onError('Could not open the map. Check your backend connection.')}/>;
}
const styles=StyleSheet.create({map:{flex:1,backgroundColor:'#eaf0e7'}});
