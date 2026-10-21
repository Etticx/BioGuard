import {useCallback,useState} from 'react';
import {Modal,Platform,StyleSheet,View} from 'react-native';
import {Button,Text} from 'react-native-paper';
import {SafeAreaView} from 'react-native-safe-area-context';
import {ElminaMap} from './ElminaMap';
import {isElminaPoint,type GeoPoint} from '../services/elminaMap';
import {colors} from '../theme';
export function DemoLocationPicker({initial,onDone,onCancel}:{initial?:GeoPoint|null;onDone:(point:GeoPoint)=>void;onCancel:()=>void}){
 const [point,setPoint]=useState<GeoPoint|null>(isElminaPoint(initial)?initial:null);const [ready,setReady]=useState(false);const [error,setError]=useState('');const [attempt,setAttempt]=useState(0);
 const onReady=useCallback(()=>{setReady(true);setError('');},[]);const onError=useCallback((message:string)=>{setError(message);setReady(false);},[]);
 return <Modal visible animationType="slide" onRequestClose={onCancel}><SafeAreaView style={styles.screen}>
  <View style={styles.heading}><Text variant="titleLarge">Pin plant location</Text><Text style={styles.hint}>{Platform.OS==='web'?'Move the map under the red pin. Scroll or pinch to zoom.':'Move the map under the red pin. Pinch to zoom.'}</Text></View>
  <View style={styles.map}><ElminaMap key={attempt} initial={initial} onPoint={setPoint} onReady={onReady} onError={onError}/></View>
  <View style={styles.footer}><Text style={styles.hint}>Elmina Lakeside pilot area. Mark where the plant was found.</Text>
   {!!error&&<><Text accessibilityRole="alert" style={styles.error}>{error}</Text><Button onPress={()=>{setError('');setReady(false);setAttempt(value=>value+1);}}>Retry map</Button></>}
   <Button mode="contained" disabled={!ready||!isElminaPoint(point)} onPress={()=>{if(isElminaPoint(point))onDone(point);}}>Done</Button><Button onPress={onCancel}>Cancel</Button>
  </View></SafeAreaView></Modal>;
}
const styles=StyleSheet.create({screen:{flex:1,backgroundColor:colors.background},heading:{padding:20,gap:8},hint:{color:colors.muted,fontSize:14,lineHeight:20},map:{flex:1,minHeight:200},footer:{padding:16,gap:12},error:{color:'#943A31'}});
