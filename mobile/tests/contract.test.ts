import assert from 'node:assert/strict';
import test from 'node:test';
import { parseIdentification, resolveApiUrl } from '../src/services/contract';
import { resultPresentation } from '../src/services/resultPresentation';

const valid = {
  predicted_species: 'Mimosa pudica', common_name: 'Touch-me-not',
  sdp_listed_invasive: true, confidence: 0.8,
  uncertain_identification: false, known_class_scope_only: true, supported_species_count: 9,
};

test('recognises the API response and preserves uncertainty', () => {
  assert.equal(parseIdentification(valid).confidence, 0.8);
  assert.equal(parseIdentification({ ...valid, uncertain_identification: true }).uncertain_identification, true);
});

test('rejects malformed predictions instead of showing false confidence', () => {
  for (const change of [
    { confidence: NaN }, { confidence: 2 }, { confidence: -1 }, { confidence: '80%' },
    { predicted_species: '' }, { known_class_scope_only: false },
    { common_name: undefined }, { common_name: ' ' },
    { sdp_listed_invasive: undefined }, { sdp_listed_invasive: 'false' },
    { uncertain_identification: undefined }, { supported_species_count: 0 },
  ]) {
    assert.throws(() => parseIdentification({ ...valid, ...change }));
  }
});

test('uses an explicit server address or the Expo LAN host', () => {
  assert.equal(resolveApiUrl('https://example.com/'), 'https://example.com');
  assert.equal(resolveApiUrl(undefined, '192.168.1.10:8081'), 'http://192.168.1.10:8000');
  assert.equal(resolveApiUrl(undefined, 'localhost:8081'), 'http://localhost:8000');
  assert.equal(resolveApiUrl(undefined, 'abc.exp.direct:443'), 'http://127.0.0.1:8000');
});


test('uncertain results label the identification and invasive status as tentative', () => {
  const result = parseIdentification({ ...valid, uncertain_identification: true });
  const presentation = resultPresentation(result);
  assert.equal(presentation.heading, 'Not confident.');
  assert.equal(presentation.matchLabel, 'Possible match');
  assert.equal(presentation.invasiveLabel, 'If confirmed: invasive');
  assert.equal(resultPresentation({ ...result, sdp_listed_invasive: false }).invasiveLabel,
    'If confirmed: not listed as invasive');
});

test('confident matches show the common name and scope invasive status to the list', () => {
  const result = parseIdentification(valid);
  assert.equal(result.common_name, 'Touch-me-not');
  assert.equal(resultPresentation(result).invasiveLabel, 'Invasive species');
  assert.equal(resultPresentation({ ...result, sdp_listed_invasive: false }).invasiveLabel,
    'Not listed as invasive');
});
