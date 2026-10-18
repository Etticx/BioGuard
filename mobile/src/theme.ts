import { MD3LightTheme } from 'react-native-paper';

export const colors = {
  background: '#F7F8F4',
  surface: '#FFFFFF',
  text: '#1E2822',
  muted: '#626B64',
  green: '#235B42',
  border: '#DFE5DC',
  controlBorder: '#7B8D80',
  paleGreen: '#EAF0E7',
  warning: '#785B24',
  paleWarning: '#F5EFDF',
};

export const theme = {
  ...MD3LightTheme,
  roundness: 3,
  colors: {
    ...MD3LightTheme.colors,
    primary: colors.green,
    onPrimary: colors.surface,
    primaryContainer: colors.paleGreen,
    onPrimaryContainer: colors.green,
    background: colors.background,
    surface: colors.surface,
    onSurface: colors.text,
    onSurfaceVariant: colors.muted,
    outline: colors.border,
    outlineVariant: colors.border,
    secondaryContainer: colors.paleGreen,
    onSecondaryContainer: colors.green,
    error: '#943A31',
  },
};
