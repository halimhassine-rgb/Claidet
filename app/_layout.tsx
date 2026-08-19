import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { useColorScheme } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { registerBackgroundAlertCheck } from '../src/services/backgroundTask';
import { ensureNotificationSetup } from '../src/services/notifications';
import { AlertsProvider } from '../src/state/AlertsContext';

export default function RootLayout() {
  const scheme = useColorScheme();

  useEffect(() => {
    ensureNotificationSetup().catch(() => {});
    registerBackgroundAlertCheck().catch(() => {});
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
      <AlertsProvider>
        <Stack screenOptions={{ headerShadowVisible: false }}>
          <Stack.Screen name="index" options={{ title: 'Mes alertes' }} />
          <Stack.Screen
            name="add-alert"
            options={{ presentation: 'modal', title: 'Nouvelle alerte' }}
          />
        </Stack>
      </AlertsProvider>
    </SafeAreaProvider>
  );
}
