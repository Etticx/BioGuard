import {useCallback,useState} from 'react';
import {View} from 'react-native';
import {Text} from 'react-native-paper';
import {ElminaMap} from './ElminaMap';
import {isElminaPoint,type GeoPoint} from '../services/elminaMap';
const ignore=()=>{};
export function ReportLocationMap({point}:{point:GeoPoint|null|undefined}){
 const [error,setError]=useState('');const ready=useCallback(()=>setError(''),[]);
 if(!isElminaPoint(point))return <Text>The original report has no live-map location.</Text>;
 return <View style={{gap:6}}><View style={{height:310,borderRadius:10,overflow:'hidden'}}><ElminaMap mode="view" initial={point} onPoint={ignore} onReady={ready} onError={setError}/></View>{!!error&&<Text accessibilityRole="alert">{error}</Text>}</View>;
}
