import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

import type { PriceAlert } from '../types/alert';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function ensureNotificationSetup(): Promise<boolean> {
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('price-alerts', {
      name: 'Alertes de cours',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
    });
  }

  const current = await Notifications.getPermissionsAsync();
  if (current.granted || current.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL) {
    return true;
  }
  const requested = await Notifications.requestPermissionsAsync({
    ios: { allowAlert: true, allowBadge: true, allowSound: true },
  });
  return requested.granted;
}

export async function notifyThresholdCrossed(alert: PriceAlert, price: number): Promise<void> {
  const verb = alert.direction === 'above' ? 'a dépassé' : 'est passé sous';
  await Notifications.scheduleNotificationAsync({
    content: {
      title: `${alert.displayName} : seuil atteint`,
      body: `${alert.displayName} (${alert.symbol}) ${verb} ${alert.threshold} ${alert.currency}. Cours actuel : ${price.toFixed(2)} ${alert.currency}.`,
      sound: true,
      data: { alertId: alert.id },
    },
    trigger: null,
  });
}
