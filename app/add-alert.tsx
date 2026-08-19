import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { useTheme } from '../src/theme';
import { useAlerts } from '../src/state/AlertsContext';
import { fetchQuote, searchSymbols, StockApiError, type StockSearchResult } from '../src/services/stockApi';
import type { AlertDirection } from '../src/types/alert';

export default function AddAlertScreen() {
  const router = useRouter();
  const colors = useTheme();
  const { addAlert } = useAlerts();

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [selected, setSelected] = useState<StockSearchResult | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [currency, setCurrency] = useState('EUR');
  const [priceLoading, setPriceLoading] = useState(false);

  const [direction, setDirection] = useState<AlertDirection>('above');
  const [threshold, setThreshold] = useState('');
  const [saving, setSaving] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (selected || query.trim().length < 2) {
      setResults([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      setSearchError(null);
      try {
        const found = await searchSymbols(query);
        setResults(found);
      } catch (err) {
        setSearchError(err instanceof StockApiError ? err.message : 'Recherche indisponible.');
      } finally {
        setSearching(false);
      }
    }, 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, selected]);

  const selectSymbol = async (result: StockSearchResult) => {
    setSelected(result);
    setQuery(result.name);
    setResults([]);
    setPriceLoading(true);
    try {
      const quote = await fetchQuote(result.symbol);
      setCurrentPrice(quote.price);
      setCurrency(quote.currency);
    } catch {
      setCurrentPrice(null);
    } finally {
      setPriceLoading(false);
    }
  };

  const clearSelection = () => {
    setSelected(null);
    setQuery('');
    setCurrentPrice(null);
    setThreshold('');
  };

  const parsedThreshold = Number(threshold.replace(',', '.'));
  const canSave = !!selected && !isNaN(parsedThreshold) && parsedThreshold > 0 && !saving;

  const onSave = async () => {
    if (!selected || !canSave) return;
    setSaving(true);
    try {
      await addAlert({
        symbol: selected.symbol,
        displayName: selected.name,
        exchange: selected.exchange,
        currency,
        direction,
        threshold: parsedThreshold,
      });
      router.back();
    } finally {
      setSaving(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.background }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={[styles.label, { color: colors.textMuted }]}>Action</Text>
        <View style={[styles.inputRow, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Ionicons name="search" size={18} color={colors.textMuted} />
          <TextInput
            value={query}
            onChangeText={(t) => {
              setQuery(t);
              setSelected(null);
              setCurrentPrice(null);
            }}
            placeholder="Ex : LVMH, Apple, Air Liquide..."
            placeholderTextColor={colors.textMuted}
            style={[styles.input, { color: colors.text }]}
            autoCorrect={false}
          />
          {selected && (
            <Pressable onPress={clearSelection} hitSlop={8}>
              <Ionicons name="close-circle" size={18} color={colors.textMuted} />
            </Pressable>
          )}
        </View>

        {searching && <ActivityIndicator style={{ marginTop: 8 }} color={colors.accent} />}
        {searchError && <Text style={[styles.error, { color: colors.danger }]}>{searchError}</Text>}

        {results.length > 0 && (
          <View style={[styles.results, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            {results.map((r) => (
              <Pressable
                key={`${r.symbol}-${r.exchange}`}
                onPress={() => selectSymbol(r)}
                style={({ pressed }) => [styles.resultRow, { opacity: pressed ? 0.6 : 1 }]}
              >
                <Text style={[styles.resultName, { color: colors.text }]} numberOfLines={1}>
                  {r.name}
                </Text>
                <Text style={[styles.resultMeta, { color: colors.textMuted }]}>
                  {r.symbol}
                  {r.exchange ? ` · ${r.exchange}` : ''}
                </Text>
              </Pressable>
            ))}
          </View>
        )}

        {selected && (
          <View style={[styles.quoteBox, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <Text style={[styles.quoteSymbol, { color: colors.text }]}>{selected.symbol}</Text>
            {priceLoading ? (
              <ActivityIndicator color={colors.accent} />
            ) : currentPrice != null ? (
              <Text style={[styles.quotePrice, { color: colors.accent }]}>
                {currentPrice.toFixed(2)} {currency}
              </Text>
            ) : (
              <Text style={[styles.quotePrice, { color: colors.textMuted }]}>Prix indisponible</Text>
            )}
          </View>
        )}

        <Text style={[styles.label, { color: colors.textMuted, marginTop: 24 }]}>Condition</Text>
        <View style={styles.segmented}>
          <Pressable
            onPress={() => setDirection('above')}
            style={[
              styles.segment,
              { borderColor: colors.border },
              direction === 'above' && { backgroundColor: colors.accent, borderColor: colors.accent },
            ]}
          >
            <Ionicons
              name="trending-up"
              size={16}
              color={direction === 'above' ? '#FFFFFF' : colors.text}
            />
            <Text style={[styles.segmentText, { color: direction === 'above' ? '#FFFFFF' : colors.text }]}>
              Dépasse
            </Text>
          </Pressable>
          <Pressable
            onPress={() => setDirection('below')}
            style={[
              styles.segment,
              { borderColor: colors.border },
              direction === 'below' && { backgroundColor: colors.accent, borderColor: colors.accent },
            ]}
          >
            <Ionicons
              name="trending-down"
              size={16}
              color={direction === 'below' ? '#FFFFFF' : colors.text}
            />
            <Text style={[styles.segmentText, { color: direction === 'below' ? '#FFFFFF' : colors.text }]}>
              Descend sous
            </Text>
          </Pressable>
        </View>

        <Text style={[styles.label, { color: colors.textMuted, marginTop: 24 }]}>
          Seuil ({currency})
        </Text>
        <View style={[styles.inputRow, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <TextInput
            value={threshold}
            onChangeText={setThreshold}
            placeholder="Ex : 500"
            placeholderTextColor={colors.textMuted}
            keyboardType="decimal-pad"
            style={[styles.input, { color: colors.text }]}
          />
        </View>

        <Pressable
          onPress={onSave}
          disabled={!canSave}
          style={[styles.saveButton, { backgroundColor: canSave ? colors.accent : colors.border }]}
        >
          {saving ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.saveButtonText}>Créer l'alerte</Text>
          )}
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, paddingBottom: 60 },
  label: { fontSize: 13, fontWeight: '600', marginBottom: 8, textTransform: 'uppercase' },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    height: 48,
  },
  input: { flex: 1, fontSize: 16, height: '100%' },
  error: { fontSize: 13, marginTop: 8 },
  results: {
    marginTop: 8,
    borderWidth: 1,
    borderRadius: 12,
    overflow: 'hidden',
  },
  resultRow: { paddingHorizontal: 14, paddingVertical: 12 },
  resultName: { fontSize: 15, fontWeight: '600' },
  resultMeta: { fontSize: 12, marginTop: 2 },
  quoteBox: {
    marginTop: 12,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  quoteSymbol: { fontSize: 14, fontWeight: '600' },
  quotePrice: { fontSize: 16, fontWeight: '700' },
  segmented: { flexDirection: 'row', gap: 10 },
  segment: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1,
    borderRadius: 12,
    height: 44,
  },
  segmentText: { fontSize: 14, fontWeight: '600' },
  saveButton: {
    marginTop: 32,
    height: 52,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  saveButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
});
