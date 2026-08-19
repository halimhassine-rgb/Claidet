export interface StockQuote {
  symbol: string;
  price: number;
  currency: string;
  exchange?: string;
  marketState?: string;
}

export interface StockSearchResult {
  symbol: string;
  name: string;
  exchange?: string;
  type?: string;
}

const CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/';
const SEARCH_URL = 'https://query2.finance.yahoo.com/v1/finance/search';

const COMMON_HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
  Accept: 'application/json',
};

export class StockApiError extends Error {}

export async function fetchQuote(symbol: string): Promise<StockQuote> {
  const url = `${CHART_URL}${encodeURIComponent(symbol)}?interval=1d&range=1d`;
  let response: Response;
  try {
    response = await fetch(url, { headers: COMMON_HEADERS });
  } catch {
    throw new StockApiError('Impossible de contacter le service de cotation.');
  }
  if (!response.ok) {
    throw new StockApiError(`Le service de cotation a renvoyé une erreur (${response.status}).`);
  }
  const json = await response.json();
  const result = json?.chart?.result?.[0];
  const errorMessage: string | undefined = json?.chart?.error?.description;
  if (errorMessage || !result?.meta) {
    throw new StockApiError(errorMessage ?? `Symbole "${symbol}" introuvable.`);
  }
  const meta = result.meta;
  const price = meta.regularMarketPrice;
  if (typeof price !== 'number') {
    throw new StockApiError(`Aucun prix disponible pour "${symbol}".`);
  }
  return {
    symbol: meta.symbol ?? symbol,
    price,
    currency: meta.currency ?? 'USD',
    exchange: meta.exchangeName,
    marketState: meta.marketState,
  };
}

export async function searchSymbols(query: string): Promise<StockSearchResult[]> {
  const trimmed = query.trim();
  if (trimmed.length < 1) return [];
  const url = `${SEARCH_URL}?q=${encodeURIComponent(trimmed)}&quotesCount=8&newsCount=0`;
  let response: Response;
  try {
    response = await fetch(url, { headers: COMMON_HEADERS });
  } catch {
    throw new StockApiError('Impossible de contacter le service de recherche.');
  }
  if (!response.ok) {
    throw new StockApiError(`La recherche a échoué (${response.status}).`);
  }
  const json = await response.json();
  const quotes: any[] = Array.isArray(json?.quotes) ? json.quotes : [];
  return quotes
    .filter((q) => typeof q.symbol === 'string' && (q.shortname || q.longname))
    .map((q) => ({
      symbol: q.symbol,
      name: q.shortname ?? q.longname ?? q.symbol,
      exchange: q.exchange,
      type: q.quoteType,
    }));
}
