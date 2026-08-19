import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useTheme } from '../theme';
import type { PriceAlert } from '../types/alert';
import { formatPrice, formatRelativeTime } from '../utils/format';

interface Props {
  alert: PriceAlert;
  onPress: () => void;
  onToggleActive: () => void;
  onDelete: () => void;
}

export function AlertListItem({ alert, onPress, onToggleActive, onDelete }: Props) {
  const colors = useTheme();

  let statusLabel = 'Actif';
  let statusColor = colors.success;
  if (alert.triggered) {
    statusLabel = 'Déclenchée';
    statusColor = colors.warning;
  } else if (!alert.active) {
    statusLabel = 'En pause';
    statusColor = colors.textMuted;
  }

  const directionLabel = alert.direction === 'above' ? 'Dépasse' : 'Descend sous';

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.card,
        { backgroundColor: colors.surface, borderColor: colors.border, opacity: pressed ? 0.85 : 1 },
      ]}
    >
      <View style={styles.headerRow}>
        <View style={{ flex: 1 }}>
          <Text style={[styles.symbol, { color: colors.text }]} numberOfLines={1}>
            {alert.displayName}
          </Text>
          <Text style={[styles.subtitle, { color: colors.textMuted }]} numberOfLines={1}>
            {alert.symbol}
            {alert.exchange ? ` · ${alert.exchange}` : ''}
          </Text>
        </View>
        <View style={[styles.statusPill, { borderColor: statusColor }]}>
          <Text style={[styles.statusText, { color: statusColor }]}>{statusLabel}</Text>
        </View>
      </View>

      <View style={styles.thresholdRow}>
        <Ionicons
          name={alert.direction === 'above' ? 'trending-up' : 'trending-down'}
          size={16}
          color={colors.accent}
        />
        <Text style={[styles.thresholdText, { color: colors.text }]}>
          {directionLabel} {formatPrice(alert.threshold, alert.currency)}
        </Text>
      </View>

      {alert.lastPrice != null && (
        <Text style={[styles.lastPrice, { color: colors.textMuted }]}>
          Dernier cours : {formatPrice(alert.lastPrice, alert.currency)}
          {alert.lastCheckedAt ? ` · ${formatRelativeTime(alert.lastCheckedAt)}` : ''}
        </Text>
      )}

      <View style={[styles.actionsRow, { borderTopColor: colors.border }]}>
        <Pressable onPress={onToggleActive} hitSlop={8} style={styles.actionButton}>
          <Ionicons
            name={alert.active ? 'pause' : 'play'}
            size={16}
            color={colors.textMuted}
          />
          <Text style={[styles.actionText, { color: colors.textMuted }]}>
            {alert.active ? 'Mettre en pause' : 'Réactiver'}
          </Text>
        </Pressable>
        <Pressable onPress={onDelete} hitSlop={8} style={styles.actionButton}>
          <Ionicons name="trash-outline" size={16} color={colors.danger} />
          <Text style={[styles.actionText, { color: colors.danger }]}>Supprimer</Text>
        </Pressable>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 16,
    marginBottom: 12,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  symbol: {
    fontSize: 17,
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  statusPill: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  thresholdRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 12,
  },
  thresholdText: {
    fontSize: 15,
    fontWeight: '600',
  },
  lastPrice: {
    fontSize: 13,
    marginTop: 6,
  },
  actionsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 14,
    paddingTop: 12,
    borderTopWidth: 1,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  actionText: {
    fontSize: 13,
    fontWeight: '600',
  },
});
