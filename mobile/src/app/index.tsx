import { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Animated, Image, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Text } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Glyph } from '../components/Glyph';
import { PlantSketch } from '../components/PlantSketch';
import { PlantResult } from '../components/PlantResult';
import { resultPresentation } from '../services/resultPresentation';
import { useScan } from '../hooks/useScan';
import { router } from 'expo-router';
import { TeamReports } from '../components/TeamReports';
import { TeamSignIn } from '../components/TeamSignIn';
import { ScreenShell } from '../components/ScreenShell';
import { useTeamSession } from '../hooks/useTeamSession';
import { colors } from '../theme';
import { ActionButton as Button } from '../components/ActionButton';
import { AccountActions } from '../components/AccountActions';

export default function IdentifyScreen() {
  const {session,endSession}=useTeamSession();
  const privateBeta=process.env.EXPO_PUBLIC_PRIVATE_BETA==='1';
  const { photo, result, busy, selecting, error, selectPhoto, identify, reset } = useScan();
  const [fade] = useState(() => new Animated.Value(1));
  const scroll = useRef<ScrollView>(null);
  const disabled = busy || selecting;

  useEffect(() => {
    let cancelled = false;
    void AccessibilityInfo.isReduceMotionEnabled().then((reduced) => {
      if (cancelled || reduced) return;
      fade.setValue(0);
      Animated.timing(fade, { toValue: 1, duration: 180, useNativeDriver: Platform.OS !== 'web' }).start();
    }).catch(() => {});
    scroll.current?.scrollTo({ y: 0, animated: false });
    return () => { cancelled = true; fade.stopAnimation(); };
  }, [photo, result, fade]);

  if(privateBeta&&(!session||session.user.must_change_password))return <ScreenShell><View style={{gap:18}}><Text variant="labelLarge">BioGuard · Private beta</Text><TeamSignIn/><Button onPress={()=>router.push('/beta-information')}>About this test</Button></View></ScreenShell>;

  if(session?.user.role==='ecology')return <ScreenShell><TeamReports onBack={()=>router.replace('/')} home/></ScreenShell>;

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView ref={scroll} contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          <View style={styles.brand} accessibilityLabel="BioGuard">
            <View style={styles.mark}><Glyph name="leaf" size={23} /></View>
            <Text style={styles.brandName}>BioGuard</Text>
          </View>
          <View style={styles.navigation}>
            <Button mode="contained-tonal" disabled={disabled} onPress={() => router.push('/team')}>My sightings</Button>
            {session && <AccountActions disabled={disabled} />}
          </View>
          <Animated.View style={[styles.body, { opacity: fade }]}>
            {!photo ? <>
              <View style={styles.intro}>
                <Text accessibilityRole="header" style={styles.title}>Identify a plant.</Text>
                <Text style={styles.subtitle}>Choose a clear plant photo.</Text>
              </View>
              <View style={styles.illustration}><PlantSketch /></View>
            </> : <>
              <View style={styles.intro}>
                <Text accessibilityRole="header" style={styles.title}>
                  {result ? resultPresentation(result).heading : 'Ready for a closer look?'}
                </Text>
                {!result && <Text style={styles.subtitle}>Keep the leaves clearly in view.</Text>}
              </View>
              <View style={[styles.photoFrame, result && styles.resultPhoto]}>
                <Image source={{ uri: photo.uri }} style={styles.photo} resizeMode="contain"
                  accessibilityLabel="Selected plant photo" />
              </View>
              {result && <PlantResult result={result} />}
            </>}
            <View style={styles.actions}>
              {error && <View style={styles.error} accessibilityLiveRegion="assertive">
                <Glyph name="info" size={18} color="#943A31" />
                <Text style={styles.errorText}>{error}</Text>
              </View>}
              {!photo ? <>
                <Button mode="contained" onPress={() => { void selectPhoto('camera'); }}
                  icon={({ color, size }) => <Glyph name="camera" color={color} size={size} />}
                  disabled={disabled} style={styles.button} contentStyle={styles.buttonContent}
                  labelStyle={styles.buttonLabel} accessibilityLabel="Take a plant photo">
                  Take photo
                </Button>
                <Button mode="outlined" onPress={() => { void selectPhoto('gallery'); }}
                  icon={({ color, size }) => <Glyph name="gallery" color={color} size={size} />}
                  disabled={disabled} style={[styles.button, styles.secondary]}
                  contentStyle={styles.buttonContent} labelStyle={styles.buttonLabel}
                  accessibilityLabel="Choose a plant photo from the gallery">
                  Choose photo
                </Button>
                {selecting && <ActivityIndicator size="small" style={styles.selectionSpinner} />}
              </> : result ? <>
                <Button mode="contained" onPress={() => router.push('/report')} style={styles.button}
                  contentStyle={styles.buttonContent} labelStyle={styles.buttonLabel}>Report sighting</Button>
                <Button mode="outlined" onPress={reset} style={styles.button}
                  contentStyle={styles.buttonContent} labelStyle={styles.buttonLabel}>Try another photo</Button>
              </> : <>
                <Button mode="contained" onPress={() => { void identify(session??undefined,()=>{if(session)endSession(session);}); }}
                  loading={busy} disabled={disabled}
                  icon={busy ? undefined : ({ color, size }) =>
                    <Glyph name="arrow" color={color} size={size} />}
                  style={styles.button} contentStyle={styles.buttonContent}
                  labelStyle={styles.buttonLabel}
                  accessibilityLabel={busy ? 'Identifying plant' : 'Identify plant'}
                  accessibilityState={{ busy }}>
                  {busy ? 'Identifying…' : 'Identify'}
                </Button>
                <Button mode="outlined" disabled={disabled} onPress={() => router.push('/report')}>Report without identification</Button>
                <Button mode="text" onPress={reset} disabled={disabled}
                  contentStyle={styles.buttonContent} labelStyle={styles.buttonLabel}>
                  Change photo
                </Button>
              </>}
              {!photo && <Text style={styles.footer}>9 supported species</Text>}
            </View>
          </Animated.View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  scroll: { flexGrow: 1, paddingHorizontal: 24, paddingTop: 18, paddingBottom: 24 },
  content: { flex: 1, width: '100%', maxWidth: 420, alignSelf: 'center' },
  brand: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 10, marginBottom: 20 },
  mark: { width: 40, height: 40, borderRadius: 12, backgroundColor: colors.paleGreen,
    alignItems: 'center', justifyContent: 'center' },
  brandName: { fontSize: 20, fontWeight: '600', color: colors.text, letterSpacing: -0.4 },
  body: { flex: 1 },
  navigation: { gap: 12, marginBottom: 28 },
  headerActions: { marginLeft: 'auto', flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'flex-end' },
  logoutError: { color: '#943A31', lineHeight: 22, marginBottom: 16 },
  intro: { gap: 10, marginBottom: 20 },
  title: { fontSize: 26, lineHeight: 34, fontWeight: '600', color: colors.text, letterSpacing: -0.6 },
  subtitle: { fontSize: 16, lineHeight: 24, color: colors.muted },
  illustration: { minHeight: 260, height: 300, maxHeight: 340, flexGrow: 1,
    marginBottom: 30, justifyContent: 'center' },
  photoFrame: { width: '100%', aspectRatio: 1, borderRadius: 12, overflow: 'hidden',
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, marginBottom: 24 },
  resultPhoto: { aspectRatio: 1.18, marginBottom: 24 },
  photo: { width: '100%', height: '100%' },
  actions: { gap: 12, marginTop: 'auto', paddingTop: 6 },
  button: { borderRadius: 12 },
  secondary: { borderColor: colors.controlBorder, backgroundColor: colors.surface },
  buttonContent: { minHeight: 54, paddingVertical: 3 },
  buttonLabel: { fontSize: 16, fontWeight: '600', letterSpacing: 0 },
  footer: { marginTop: 6, textAlign: 'center', color: colors.muted, fontSize: 14, lineHeight: 20 },
  selectionSpinner: { marginTop: 4 },
  error: { flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: '#F7EBE8', padding: 12, borderRadius: 10 },
  errorText: { flex: 1, color: '#943A31', fontSize: 14, lineHeight: 21 },
});


