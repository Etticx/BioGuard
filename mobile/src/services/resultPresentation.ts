import type { Identification } from './contract';

export function resultPresentation(result: Identification) {
  const uncertain = result.uncertain_identification;
  return {
    heading: uncertain ? 'Not confident.' : 'Your result.',
    matchLabel: uncertain ? 'Possible match' : 'Suggested match',
    invasiveLabel: result.sdp_listed_invasive
      ? uncertain ? 'If confirmed: invasive' : 'Invasive species'
      : uncertain ? 'If confirmed: not listed as invasive' : 'Not listed as invasive',
  };
}
