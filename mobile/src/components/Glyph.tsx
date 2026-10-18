import Svg, { Circle, Path, Rect } from 'react-native-svg';
import { colors } from '../theme';

type Name = 'leaf' | 'camera' | 'gallery' | 'arrow' | 'info' | 'back' | 'settings' | 'drafts' | 'updates' | 'refresh';

export function Glyph({ name, size = 22, color = colors.green }: {
  name: Name; size?: number; color?: string;
}) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={color} strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round"
      aria-hidden>
      {name === 'leaf' && <>
        <Path d="M20.5 3.5C12 2 4.5 5.5 4.5 12.5c0 4.1 2.7 6.5 6.6 6.5 7.1 0 9.4-7.2 9.4-15.5Z" />
        <Path d="M3 21c2-5 6.5-9.5 13-13M8.5 14.5l.1-4.5M11.5 11.5l4.5.1" />
      </>}
      {name === 'camera' && <>
        <Path d="M8 5.5 9.5 3.5h5L16 5.5h3.5a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-15a2 2 0 0 1-2-2v-11a2 2 0 0 1 2-2Z" />
        <Circle cx="12" cy="13" r="4" />
      </>}
      {name === 'gallery' && <>
        <Path d="M4 7H3a1.5 1.5 0 0 0-1.5 1.5v12A1.5 1.5 0 0 0 3 22h12a1.5 1.5 0 0 0 1.5-1.5V20" />
        <Rect x="6" y="2" width="16" height="16" rx="2" />
        <Circle cx="11" cy="7" r="1.3" />
        <Path d="m7 16 5-5 3 3 3-4 3 4" />
      </>}
      {name === 'arrow' && <Path d="M5 12h14m-5-5 5 5-5 5" />}
      {name === 'back' && <Path d="M19 12H5m5-5-5 5 5 5" />}
      {name === 'settings' && <><Path d="m9 3-.5 2-2 1L4.5 5.5l-2 3.5L4 10.5v3L2.5 15l2 3.5 2-.5 2 1 .5 2h4l.5-2 2-1 2 .5 2-3.5-1.5-1.5v-3L20 9l-2-3.5L16 6l-2-1-.5-2Z"/><Circle cx="11.5" cy="12" r="3"/></>}
      {name === 'drafts' && <><Rect x="5" y="3" width="14" height="18" rx="2"/><Path d="M9 8h6M9 12h6M9 16h4"/></>}
      {name === 'updates' && <><Path d="M5 17h14l-2-3v-4a5 5 0 0 0-10 0v4ZM10 21h4M12 3V2"/></>}
      {name === 'refresh' && <><Path d="M20 8a8 8 0 1 0 0 8M20 3v5h-5"/></>}
      {name === 'info'  && <>
        <Circle cx="12" cy="12" r="9" />
        <Path d="M12 11v5M12 7.5v.1" />
      </>}
    </Svg>
  );
}

