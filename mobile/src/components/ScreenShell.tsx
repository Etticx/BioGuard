import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors } from '../theme';
import { Glyph } from './Glyph';
export function ScreenShell({ children }: { children: ReactNode }) {
  return <SafeAreaView style={styles.screen}><ScrollView contentContainerStyle={styles.scroll}
    keyboardShouldPersistTaps="handled"><View style={styles.content}>
    <View style={styles.brand}><View style={styles.mark}><Glyph name="leaf" size={23}/></View>
      <Text style={styles.name}>BioGuard</Text></View>{children}
  </View></ScrollView></SafeAreaView>;
}
const styles=StyleSheet.create({screen:{flex:1,backgroundColor:colors.background},scroll:{padding:24,paddingTop:18,flexGrow:1},
  content:{width:'100%',maxWidth:420,alignSelf:'center'},brand:{flexDirection:'row',alignItems:'center',gap:10,marginBottom:36},
  mark:{width:40,height:40,borderRadius:12,backgroundColor:colors.paleGreen,alignItems:'center',justifyContent:'center'},
  name:{fontSize:20,fontWeight:'600',color:colors.text,letterSpacing:-0.4}});
