# Claidet — Alertes de cours boursiers

Application mobile (iOS / Android) qui envoie une notification dès qu'une action franchit un seuil de prix que vous avez défini (ex. LVMH au-dessus de 500 €).

Construite avec [Expo](https://expo.dev) / React Native + TypeScript.

## Fonctionnalités

- Recherche d'une action par nom ou symbole (Yahoo Finance) et création d'une alerte "dépasse" ou "descend sous" un seuil.
- Vérification automatique en arrière-plan (best-effort, contrôlée par le système) toutes les ~15 minutes minimum.
- Vérification active toutes les 60 secondes tant que l'application est ouverte, + bouton "tirer pour rafraîchir".
- Notification locale (avec son) dès qu'un seuil est franchi ; l'alerte passe alors au statut "Déclenchée" et peut être réinitialisée.
- Mise en pause / suppression des alertes, aucune donnée envoyée à un serveur : tout est stocké localement sur le téléphone.

## Limites importantes à connaître

- **Pas de backend** : les prix sont récupérés directement depuis l'API publique (non officielle) de Yahoo Finance, à la demande. Aucune clé d'API n'est nécessaire, mais ce service peut ponctuellement être limité ou instable.
- **Exécution en arrière-plan limitée par l'OS** : iOS et Android ne garantissent pas une exécution périodique exacte. Une alerte peut donc être déclenchée avec un léger retard si l'app est fermée depuis longtemps. Pour une fiabilité maximale, gardez l'app installée et ouvrez-la de temps en temps ; sur Android, désactivez l'optimisation de batterie pour l'app.
- Pour du "temps réel" garanti même app fermée, il faudrait un serveur qui surveille les cours et envoie des notifications push — non inclus ici pour rester 100 % local et gratuit.

## Démarrer en développement

```bash
npm install
npx expo start
```

Scannez le QR code avec l'app **Expo Go** (iOS/Android) pour tester rapidement. Les notifications planifiées fonctionnent dans Expo Go, mais la tâche d'arrière-plan (`expo-background-task`) nécessite un **build de développement** (`expo-dev-client`) ou un build de production — elle est ignorée silencieusement dans Expo Go.

## Installer l'app sur votre téléphone

Deux options :

### Option A — Build interne avec EAS (recommandé)

```bash
npm install -g eas-cli
eas login
eas build:configure
eas build --profile preview --platform android   # ou ios
```

EAS Build (gratuit avec des quotas mensuels) génère un `.apk`/`.ipa` que vous installez directement, ou un lien à ouvrir sur votre téléphone. Voir https://docs.expo.dev/build/introduction/.

### Option B — Build local

```bash
npx expo run:android   # nécessite Android Studio
npx expo run:ios       # nécessite un Mac + Xcode
```

## Structure du projet

```
app/                  écrans (Expo Router)
  _layout.tsx          layout racine, init notifications + tâche de fond
  index.tsx             liste des alertes
  add-alert.tsx          création d'une alerte (recherche + seuil)
src/
  types/alert.ts          modèle de données d'une alerte
  storage/alertsStorage.ts persistance locale (AsyncStorage)
  services/stockApi.ts      appels à l'API de cotation / recherche
  services/alertChecker.ts   logique de vérification des seuils
  services/notifications.ts   permissions + envoi des notifications locales
  services/backgroundTask.ts   tâche planifiée en arrière-plan
  state/AlertsContext.tsx      état global des alertes (React context)
  components/, theme.ts, utils/  UI et utilitaires
```
