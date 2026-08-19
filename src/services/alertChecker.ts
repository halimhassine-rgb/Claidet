import { loadAlerts, saveAlerts } from '../storage/alertsStorage';
import type { PriceAlert } from '../types/alert';
import { fetchQuote } from './stockApi';
import { notifyThresholdCrossed } from './notifications';

function isThresholdCrossed(alert: PriceAlert, price: number): boolean {
  return alert.direction === 'above' ? price >= alert.threshold : price <= alert.threshold;
}

/**
 * Checks every active, not-yet-triggered alert against the latest price and fires a
 * local notification for any that crossed their threshold. Shared by the foreground
 * polling loop and the headless background task so both paths stay in sync.
 */
export async function checkAlertsOnce(): Promise<{ checked: number; triggered: number }> {
  const alerts = await loadAlerts();
  const pending = alerts.filter((a) => a.active && !a.triggered);
  if (pending.length === 0) {
    return { checked: 0, triggered: 0 };
  }

  let triggeredCount = 0;
  const now = Date.now();

  for (const alert of pending) {
    try {
      const quote = await fetchQuote(alert.symbol);
      alert.lastPrice = quote.price;
      alert.lastCheckedAt = now;

      if (isThresholdCrossed(alert, quote.price)) {
        alert.triggered = true;
        alert.triggeredAt = now;
        alert.triggeredPrice = quote.price;
        await notifyThresholdCrossed(alert, quote.price);
        triggeredCount += 1;
      }
    } catch {
      // A single symbol failing to fetch shouldn't block the rest of the batch.
    }
  }

  await saveAlerts(alerts);
  return { checked: pending.length, triggered: triggeredCount };
}
