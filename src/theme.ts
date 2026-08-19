import { useColorScheme } from 'react-native';

const palette = {
  light: {
    background: '#F4F6F9',
    surface: '#FFFFFF',
    border: '#E2E6EC',
    text: '#0B1B2B',
    textMuted: '#5B6B7C',
    primary: '#0B1B2B',
    accent: '#1C7ED6',
    success: '#2F9E44',
    danger: '#E03131',
    warning: '#F08C00',
  },
  dark: {
    background: '#0B0F14',
    surface: '#161C24',
    border: '#262E38',
    text: '#F2F5F8',
    textMuted: '#9AA7B4',
    primary: '#F2F5F8',
    accent: '#4DABF7',
    success: '#51CF66',
    danger: '#FF6B6B',
    warning: '#FFA94D',
  },
};

export type ThemeColors = typeof palette.light;

export function useTheme(): ThemeColors {
  const scheme = useColorScheme();
  return scheme === 'dark' ? palette.dark : palette.light;
}
