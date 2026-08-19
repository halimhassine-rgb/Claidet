export type AlertDirection = 'above' | 'below';

export interface PriceAlert {
  id: string;
  symbol: string;
  displayName: string;
  exchange?: string;
  currency: string;
  direction: AlertDirection;
  threshold: number;
  active: boolean;
  triggered: boolean;
  createdAt: number;
  lastPrice?: number;
  lastCheckedAt?: number;
  triggeredAt?: number;
  triggeredPrice?: number;
}

export type NewAlertInput = Pick<
  PriceAlert,
  'symbol' | 'displayName' | 'exchange' | 'currency' | 'direction' | 'threshold'
>;
