import { useLayoutEffect, useRef, useState } from 'react';
import { Image, Modal, PanResponder, StyleSheet, View, type GestureResponderEvent, type ViewStyle } from 'react-native';
import { Button, Text } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Circle, Path } from 'react-native-svg';
import { DEMO_MAP_ID, imageFrame, panPoint, type DemoPin, type Point, type Size } from '../services/demoMap';
import { colors } from '../theme';
const mapImage = require('../../assets/elmina-city-centre-demo.png');
type GestureStart={x:number;y:number;distance:number;count:number;point:Point;zoom:number};
function touchPosition(event:GestureResponderEvent){
 const touches=event.nativeEvent.touches;
 const a=touches[0]??event.nativeEvent,b=touches[1];
 return {x:b?(a.pageX+b.pageX)/2:a.pageX,y:b?(a.pageY+b.pageY)/2:a.pageY,
  distance:b?Math.hypot(a.pageX-b.pageX,a.pageY-b.pageY):0,count:b?2:1};
}
export function DemoLocationPicker({initial,onDone,onCancel}:{initial?:DemoPin|null;onDone:(pin:DemoPin)=>void;onCancel:()=>void}){
 const [point,setPoint]=useState<Point>(initial??{x:0.5,y:0.5});
 const [zoom,setZoom]=useState(initial?2:1);const [size,setSize]=useState<Size>({width:0,height:0});
 const [loaded,setLoaded]=useState(false);const [failed,setFailed]=useState(false);
 const state=useRef({point,zoom,size});useLayoutEffect(()=>{state.current={point,zoom,size};},[point,zoom,size]);const start=useRef<GestureStart|null>(null);
 function begin(event:GestureResponderEvent){start.current={...touchPosition(event),point:state.current.point,zoom:state.current.zoom};}
 // PanResponder stores callbacks; refs are read only when a gesture fires, not during creation.
 // eslint-disable-next-line react-hooks/refs
 const [responder]=useState(()=>PanResponder.create({
  onStartShouldSetPanResponder:()=>true,onMoveShouldSetPanResponder:()=>true,
  onPanResponderGrant:event=>begin(event),
  onPanResponderMove:event=>{
   const touch=touchPosition(event),base=start.current;
   if(!base||base.count!==touch.count){begin(event);return;}
   const nextZoom=Math.max(1,Math.min(5,base.distance>0&&touch.distance>0?base.zoom*touch.distance/base.distance:base.zoom));
   const frame=imageFrame(state.current.size,base.point,nextZoom);
   setZoom(nextZoom);setPoint(panPoint(base.point,touch.x-base.x,touch.y-base.y,frame.width,frame.height));
  },onPanResponderRelease:()=>{start.current=null;},onPanResponderTerminate:()=>{start.current=null;},
 }));
 const frame=imageFrame(size,point,zoom);
 return <Modal visible animationType="slide" onRequestClose={onCancel}>
  <SafeAreaView style={styles.screen}>
   <View style={styles.heading}><Text variant="titleLarge">Pin plant location</Text><Text style={styles.hint}>Move the map under the red pin. Pinch or use + and - to zoom.</Text></View>
   <View accessibilityLabel="Elmina demo map. Drag to move the map beneath the pin." style={[styles.viewport,{touchAction:'none'} as ViewStyle]} onLayout={event=>setSize(event.nativeEvent.layout)} {...responder.panHandlers}>
    {size.width>0&&<Image source={mapImage} style={[styles.image,frame]} resizeMode="stretch" onLoad={()=>setLoaded(true)} onError={()=>setFailed(true)} accessibilityLabel="Elmina City Centre demonstration map"/>}
    <View pointerEvents="none" style={styles.pin}><Svg width={36} height={48} viewBox="0 0 36 48"><Path d="M18 47 C15 42 2 29 2 18 A16 16 0 1 1 34 18 C34 29 21 42 18 47Z" fill="#C33430" stroke="white" strokeWidth={2}/><Circle cx={18} cy={18} r={5} fill="white"/></Svg></View>
   </View>
   <View style={styles.footer}>
    <View style={styles.controls}><Button mode="outlined" accessibilityLabel="Zoom out" disabled={zoom<=1} onPress={()=>setZoom(Math.max(1,zoom/1.4))}>-</Button><Text>{zoom.toFixed(1)}x</Text><Button mode="outlined" accessibilityLabel="Zoom in" disabled={zoom>=5} onPress={()=>setZoom(Math.min(5,zoom*1.4))}>+</Button><Button onPress={()=>{setPoint({x:0.5,y:0.5});setZoom(1);}}>Reset</Button></View>
    <Text style={styles.hint}>Demo map only. Mark where the plant was found; live GPS is not used.</Text>
    {failed&&<Text accessibilityRole="alert" style={styles.error}>The map could not load. Close and try again.</Text>}
    <Button mode="contained" disabled={!loaded||failed||size.width===0} onPress={()=>onDone({map_id:DEMO_MAP_ID,...point})}>Done</Button>
    <Button onPress={onCancel}>Cancel</Button>
   </View>
  </SafeAreaView>
 </Modal>;
}
const styles=StyleSheet.create({screen:{flex:1,backgroundColor:colors.background},heading:{padding:20,gap:8},hint:{color:colors.muted,fontSize:14,lineHeight:20},viewport:{flex:1,overflow:'hidden',backgroundColor:colors.paleGreen},image:{position:'absolute'},pin:{position:'absolute',left:'50%',top:'50%',marginLeft:-18,marginTop:-47,width:36,height:48},footer:{padding:16,gap:12},controls:{flexDirection:'row',alignItems:'center',justifyContent:'center',gap:12},error:{color:'#943A31'}});
