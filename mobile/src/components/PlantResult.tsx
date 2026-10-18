import { StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import type { Identification } from '../services/contract';
import { resultPresentation } from '../services/resultPresentation';
import { colors } from '../theme';
import { Glyph } from './Glyph';

export function PlantResult({ result }: { result: Identification }) {
  const presentation = resultPresentation(result);
  return (
    <View style={styles.result} accessibilityLiveRegion="polite">
      {result.uncertain_identification && <View style={styles.warning}>
        <Glyph name="info" size={20} color={colors.warning} />
        <Text style={styles.warningText}>Try a clearer photo of one plant.</Text>
      </View>}
      <Text style={styles.resultLabel}>{presentation.matchLabel}</Text>
      <Text accessibilityRole="header" selectable style={styles.commonName}>
        {result.common_name}
      </Text>
      <Text selectable style={styles.scientificName}>{result.predicted_species}</Text>
      <View style={styles.statusGroup}>
        <View style={[styles.status, result.sdp_listed_invasive && styles.invasiveStatus]}>
          <Glyph name={result.sdp_listed_invasive ? 'info' : 'leaf'} size={16}
            color={result.sdp_listed_invasive ? colors.warning : colors.muted} />
          <Text style={[styles.statusText, result.sdp_listed_invasive && styles.invasiveText]}>
            {presentation.invasiveLabel}
          </Text>
        </View>
        <Text style={styles.statusSource}>SDP species list</Text>
      </View>
      <View style={styles.confidence}>
        <Text style={styles.confidenceLabel}>Model confidence</Text>
        <Text style={[styles.confidenceValue, result.uncertain_identification && styles.invasiveText]}>
          {(result.confidence * 100).toFixed(1)}%
        </Text>
      </View>
      <Text style={styles.scope}>
        Only {result.supported_species_count} supported species. Other plants may be misidentified.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  result: { gap: 8, marginBottom: 24 },
  resultLabel: { fontSize: 14, color: colors.muted, lineHeight: 20 },
  commonName: { fontSize: 24, fontWeight: '600', color: colors.text, lineHeight: 32, letterSpacing: -0.4 },
  scientificName: { fontSize: 16, color: colors.muted, lineHeight: 24, fontStyle: 'italic' },
  statusGroup: { alignItems: 'flex-start', gap: 6, marginTop: 8 },
  status: { flexDirection: 'row', alignItems: 'center', gap: 7, maxWidth: '100%',
    backgroundColor: colors.paleGreen, paddingHorizontal: 10, paddingVertical: 7, borderRadius: 8 },
  invasiveStatus: { backgroundColor: colors.paleWarning },
  statusText: { flexShrink: 1, fontSize: 13, lineHeight: 19, fontWeight: '600', color: colors.muted },
  invasiveText: { color: colors.warning },
  statusSource: { fontSize: 12, lineHeight: 18, color: colors.muted },
  confidence: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    gap: 12, borderTopWidth: 1, borderColor: colors.border, marginTop: 10, paddingTop: 16,
    flexWrap: 'wrap' },
  confidenceLabel: { fontSize: 14, lineHeight: 22, color: colors.muted },
  confidenceValue: { fontSize: 18, lineHeight: 24, fontWeight: '600', color: colors.green },
  scope: { fontSize: 14, lineHeight: 21, color: colors.muted, marginTop: 8 },
  warning: { flexDirection: 'row', alignItems: 'center', gap: 9, padding: 12, borderRadius: 10,
    marginBottom: 10, backgroundColor: colors.paleWarning },
  warningText: { flex: 1, fontSize: 14, lineHeight: 21, color: colors.warning },
});
