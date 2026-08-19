import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useEffect, useRef } from 'react';
import { Alert, FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { AlertListItem } from '../src/components/AlertListItem';
import { useTheme } from '../src/theme';
import { useAlerts } from '../src/state/AlertsContext';

const FOREGROUND_POLL_MS = 60_000;

export default function AlertsScreen() {
  const router = useRouter();
  const colors = useTheme();
  const insets = useSafeAreaInsets();
  const { alerts, loading, refreshing, checkNow, removeAlert, toggleActive } = useAlerts();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    checkNow().catch(() => {});
    pollRef.current = setInterval(() => {
      checkNow().catch(() => {});
    }, FOREGROUND_POLL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const confirmDelete = (id: string, name: string) => {
    Alert.alert('Supprimer cette alerte ?', name, [
      { text: 'Annuler', style: 'cancel' },
      { text: 'Supprimer', style: 'destructive', onPress: () => removeAlert(id) },
    ]);
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <FlatList
        data={alerts}
        keyExtractor={(item) => item.id}
        contentContainerStyle={[
          styles.listContent,
          { paddingBottom: insets.bottom + 100 },
          alerts.length === 0 && styles.emptyContainer,
        ]}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => checkNow().catch(() => {})} />
        }
        ListEmptyComponent={
          !loading ? (
            <View style={styles.empty}>
              <Ionicons name="notifications-outline" size={40} color={colors.textMuted} />
              <Text style={[styles.emptyTitle, { color: colors.text }]}>Aucune alerte pour le moment</Text>
              <Text style={[styles.emptyText, { color: colors.textMuted }]}>
                Ajoutez une action et un seuil de prix pour être notifié dès qu'il est franchi.
              </Text>
            </View>
          ) : null
        }
        renderItem={({ item }) => (
          <AlertListItem
            alert={item}
            onPress={() => {}}
            onToggleActive={() => toggleActive(item.id)}
            onDelete={() => confirmDelete(item.id, item.displayName)}
          />
        )}
      />

      <Pressable
        onPress={() => router.push('/add-alert')}
        style={[styles.fab, { backgroundColor: colors.accent, bottom: insets.bottom + 24 }]}
      >
        <Ionicons name="add" size={28} color="#FFFFFF" />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  listContent: { padding: 16 },
  emptyContainer: { flexGrow: 1 },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    gap: 8,
  },
  emptyTitle: { fontSize: 17, fontWeight: '700', marginTop: 8 },
  emptyText: { fontSize: 14, textAlign: 'center', lineHeight: 20 },
  fab: {
    position: 'absolute',
    right: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
});
