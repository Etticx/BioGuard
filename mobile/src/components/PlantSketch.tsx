import Svg, { Circle, G, Path } from 'react-native-svg';
import { colors } from '../theme';

export function PlantSketch() {
  return (
    <Svg width="100%" height="100%" viewBox="0 0 320 300" aria-hidden>
      <Circle cx="163" cy="143" r="99" fill={colors.paleGreen} />
      <G stroke={colors.green} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <Path d="M154 249c5-30 12-76 5-148" fill="none" />
        <Path d="M161 149c-31-1-57-26-50-71 33 9 57 31 50 71Z" fill="#CEDDC6" />
        <Path d="M160 183c31 2 58-22 58-61-35 4-60 23-58 61Z" fill="#DDE8D5" />
        <Path d="M158 212c-29 2-48-17-53-48 28 0 47 17 53 48Z" fill="#E6EDE0" />
        <Path d="M159 115c-10-23-1-52 27-69 11 30 3 58-27 69Z" fill="#DDE8D5" />
        <Path d="m159 115 20-53m-18 87-41-59m40 93 48-48m-50 77-42-39" fill="none" />
        <Path d="m145 126-17-2m14-3 1-17m39 59 17 1m-13-4 1-18m-17-53 14-4" fill="none" opacity=".5" />
      </G>
      <G stroke="#A3B39E" strokeWidth="1.5" strokeLinecap="round" fill="none">
        <Path d="M53 78V57h21m172 0h21v21M53 226v21h21m172 0h21v-21" />
      </G>
    </Svg>
  );
}

