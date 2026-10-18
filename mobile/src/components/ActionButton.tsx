import type { ComponentProps } from 'react';
import { StyleSheet } from 'react-native';
import { Button } from 'react-native-paper';
import { colors } from '../theme';

export function ActionButton({ mode = 'outlined', style, contentStyle, labelStyle, ...props }: ComponentProps<typeof Button>) {
  return <Button {...props} mode={mode} style={[styles.button, mode === 'outlined' && styles.outline, mode === 'contained-tonal' && styles.tonal, style]}
    contentStyle={[styles.content, contentStyle]} labelStyle={[styles.label, labelStyle]} />;
}
const styles = StyleSheet.create({
  button: { borderRadius: 12 },
  outline: { borderColor: colors.controlBorder, backgroundColor: colors.surface },
  tonal: { borderWidth: 1, borderColor: colors.controlBorder, backgroundColor: colors.paleGreen },
  content: { minHeight: 48, paddingVertical: 2 },
  label: { fontSize: 14, fontWeight: '600', letterSpacing: 0 },
});
