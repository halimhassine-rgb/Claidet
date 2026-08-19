import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { checkAlertsOnce } from '../services/alertChecker';
import { loadAlerts, saveAlerts } from '../storage/alertsStorage';
import type { NewAlertInput, PriceAlert } from '../types/alert';

interface AlertsContextValue {
  alerts: PriceAlert[];
  loading: boolean;
  refreshing: boolean;
  addAlert: (input: NewAlertInput) => Promise<void>;
  removeAlert: (id: string) => Promise<void>;
  resetAlert: (id: string) => Promise<void>;
  toggleActive: (id: string) => Promise<void>;
  checkNow: () => Promise<{ checked: number; triggered: number }>;
}

const AlertsContext = createContext<AlertsContextValue | null>(null);

function makeId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function AlertsProvider({ children }: { children: React.ReactNode }) {
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadAlerts()
      .then(setAlerts)
      .finally(() => setLoading(false));
  }, []);

  const persist = useCallback(async (next: PriceAlert[]) => {
    setAlerts(next);
    await saveAlerts(next);
  }, []);

  const addAlert = useCallback(
    async (input: NewAlertInput) => {
      const alert: PriceAlert = {
        id: makeId(),
        symbol: input.symbol,
        displayName: input.displayName,
        exchange: input.exchange,
        currency: input.currency,
        direction: input.direction,
        threshold: input.threshold,
        active: true,
        triggered: false,
        createdAt: Date.now(),
      };
      await persist([alert, ...alerts]);
    },
    [alerts, persist]
  );

  const removeAlert = useCallback(
    async (id: string) => {
      await persist(alerts.filter((a) => a.id !== id));
    },
    [alerts, persist]
  );

  const resetAlert = useCallback(
    async (id: string) => {
      await persist(
        alerts.map((a) =>
          a.id === id
            ? { ...a, triggered: false, active: true, triggeredAt: undefined, triggeredPrice: undefined }
            : a
        )
      );
    },
    [alerts, persist]
  );

  const toggleActive = useCallback(
    async (id: string) => {
      await persist(alerts.map((a) => (a.id === id ? { ...a, active: !a.active } : a)));
    },
    [alerts, persist]
  );

  const checkNow = useCallback(async () => {
    setRefreshing(true);
    try {
      const result = await checkAlertsOnce();
      const fresh = await loadAlerts();
      setAlerts(fresh);
      return result;
    } finally {
      setRefreshing(false);
    }
  }, []);

  const value = useMemo<AlertsContextValue>(
    () => ({ alerts, loading, refreshing, addAlert, removeAlert, resetAlert, toggleActive, checkNow }),
    [alerts, loading, refreshing, addAlert, removeAlert, resetAlert, toggleActive, checkNow]
  );

  return <AlertsContext.Provider value={value}>{children}</AlertsContext.Provider>;
}

export function useAlerts(): AlertsContextValue {
  const ctx = useContext(AlertsContext);
  if (!ctx) throw new Error('useAlerts must be used within an AlertsProvider');
  return ctx;
}
