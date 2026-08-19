import AsyncStorage from '@react-native-async-storage/async-storage';

import type { PriceAlert } from '../types/alert';

const STORAGE_KEY = 'claidet.alerts.v1';

export async function loadAlerts(): Promise<PriceAlert[]> {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function saveAlerts(alerts: PriceAlert[]): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(alerts));
}
