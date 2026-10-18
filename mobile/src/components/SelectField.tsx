import { useState } from 'react';
import { View } from 'react-native';
import { Button, Menu, Text } from 'react-native-paper';
export function SelectField({label,value,options,onChange,disabled=false}:{label:string;value:string;options:{value:string;label:string}[];onChange:(value:string)=>void;disabled?:boolean}){const [open,setOpen]=useState(false);return <View style={{gap:4}}><Text>{label}</Text><Menu visible={open} onDismiss={()=>setOpen(false)} anchor={<Button mode="outlined" disabled={disabled} accessibilityLabel={label} onPress={()=>setOpen(true)}>{options.find(option=>option.value===value)?.label??'Choose'}</Button>}>{options.map(option=><Menu.Item key={option.value} title={option.label} onPress={()=>{onChange(option.value);setOpen(false);}}/>)}</Menu></View>;}
