import { SessionExpired } from '../services/requestErrors';
import type { Session } from '../services/reportContract';
import { useEffect, useRef, useState } from 'react';
import { Alert, Linking, Platform } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';
import { File, Paths } from 'expo-file-system';
import { identifyPhoto } from '../services/identify';
import type { Identification } from '../services/contract';

type Photo = { uri: string };
type Source = 'camera' | 'gallery';

function removeTemporaryPhoto(uri?: string) {
  if (!uri || Platform.OS === 'web') return;
  try {
    // Only delete our temporary copies; never the user's original library file.
    if (uri.startsWith(Paths.cache.uri)) {
      const file = new File(uri);
      if (file.exists) file.delete();
    }
  } catch { /* The OS also manages its cache. */ }
}

export function useIdentification() {
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [result, setResult] = useState<Identification | null>(null);
  const [busy, setBusy] = useState(false);
  const [selecting, setSelecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentPhoto = useRef<Photo | null>(null);
  const activeController = useRef<AbortController | null>(null);
  const selectionActive = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
    mounted.current = false;
    activeController.current?.abort();
    removeTemporaryPhoto(currentPhoto.current?.uri);
    };
  }, []);

  async function selectPhoto(source: Source) {
    if (selectionActive.current || activeController.current) return;
    selectionActive.current = true;
    setSelecting(true);
    setError(null);
    let sourceUri: string | undefined;
    let preparedUri: string | undefined;
    try {
      if (source === 'camera' && Platform.OS !== 'web') {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted) {
          Alert.alert('Camera access', 'Allow camera access to take a plant photo.',
            permission.canAskAgain
              ? [{ text: 'OK' }]
              : [{ text: 'Cancel', style: 'cancel' },
                { text: 'Open settings', onPress: () => { void Linking.openSettings(); } }]);
          return;
        }
      }
      const options: ImagePicker.ImagePickerOptions = {
        mediaTypes: ['images'], allowsEditing: false, quality: 1,
      };
      const picked = source === 'camera'
        ? await ImagePicker.launchCameraAsync(options)
        : await ImagePicker.launchImageLibraryAsync(options);
      if (picked.canceled || !picked.assets[0]) return;
      const asset = picked.assets[0];
      sourceUri = asset.uri;
      // Standardise HEIC/PNG to JPEG and bound upload size without cropping.
      const context = ImageManipulator.manipulate(asset.uri);
      if (Math.max(asset.width, asset.height) > 2048) {
        context.resize(asset.width >= asset.height ? { width: 2048 } : { height: 2048 });
      }
      const rendered = await context.renderAsync();
      const prepared = await rendered.saveAsync({ format: SaveFormat.JPEG, compress: 0.95 });
      preparedUri = prepared.uri;
      rendered.release();
      context.release();
      if (!mounted.current) {
        removeTemporaryPhoto(preparedUri);
        return;
      }
      removeTemporaryPhoto(currentPhoto.current?.uri);
      currentPhoto.current = { uri: prepared.uri };
      setPhoto(currentPhoto.current);
      setResult(null);
    } catch {
      removeTemporaryPhoto(preparedUri);
      if (mounted.current) setError('Could not open this photo. Please try another.');
    } finally {
      if (sourceUri && sourceUri !== currentPhoto.current?.uri) removeTemporaryPhoto(sourceUri);
      selectionActive.current = false;
      if (mounted.current) setSelecting(false);
    }
  }

  async function identify(session?: Session, onSessionExpired?:()=>void) {
    if (!currentPhoto.current || activeController.current || selectionActive.current) return;
    const controller = new AbortController();
    activeController.current = controller;
    setBusy(true);
    setError(null);
    let timedOut = false;
    const timeout = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 45_000);
    try {
      const prediction = await identifyPhoto(currentPhoto.current.uri, controller.signal, session);
      if (mounted.current && !controller.signal.aborted) setResult(prediction);
    } catch (failure) {
      if(failure instanceof SessionExpired){onSessionExpired?.();return;}
      if (mounted.current) {
        const message = timedOut ? 'Taking too long. Please try again.'
          : failure instanceof Error && !/fetch|network|abort|connection/i.test(failure.message)
            ? failure.message
            : 'Could not connect to BioGuard. Please try again.';
        setError(message);
      }
    } finally {
      clearTimeout(timeout);
      activeController.current = null;
      if (mounted.current) setBusy(false);
    }
  }

  function reset() {
    if (activeController.current || selectionActive.current) return;
    removeTemporaryPhoto(currentPhoto.current?.uri);
    currentPhoto.current = null;
    setPhoto(null);
    setResult(null);
    setError(null);
  }

  return { photo, result, busy, selecting, error, selectPhoto, identify, reset };
}

