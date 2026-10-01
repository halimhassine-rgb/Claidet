# Reelicious Mobile (Android)

Version mobile de Reelicious : une vraie application Android, qui tourne
entièrement sur le téléphone, **sans serveur**. Même principe que
l'application de bureau : tu colles un lien Instagram, l'appli télécharge
le reel, en tire les ingrédients/étapes (avec l'aide de Claude, via un
appel direct depuis le téléphone — même mécanisme et même coût que sur
l'appli de bureau), puis supprime la vidéo. **Aucune vidéo n'est
conservée** sur le téléphone, contrairement à la version bureau : seules
l'image de couverture et les données texte de la recette restent
enregistrées, pour garder l'appli légère.

## Récupérer l'application (aucune ligne de commande nécessaire)

Cette appli se compile automatiquement à chaque mise à jour du code, sur
les machines de GitHub (nécessaire : mon environnement de développement
n'a pas accès à certains services Google requis pour compiler une appli
Android — la compilation se fait donc ailleurs, mais reste 100%
automatique).

Pour récupérer le fichier à installer sur ton téléphone :

1. Va sur la page du dépôt GitHub, onglet **Actions**.
2. Clique sur le dernier run réussi de **« Build Reelicious Android (debug
   APK) »** (coche verte).
3. Tout en bas de la page, dans **Artifacts**, clique sur
   **reelicious-debug-apk** pour le télécharger (fichier `.zip`).
4. Décompresse le `.zip` : tu obtiens `app-debug.apk`.
5. Transfère ce fichier sur ton téléphone Android (par mail, par
   WhatsApp/Telegram à toi-même, par clé USB, etc.) et ouvre-le depuis le
   téléphone pour l'installer.
6. Android va probablement afficher un avertissement du type « installation
   d'applications inconnues bloquée » : c'est normal pour toute appli
   installée hors du Play Store (un APK de debug n'est pas publié
   dessus). Il suffit d'autoriser l'installation pour cette source dans
   les réglages proposés à l'écran, puis de relancer l'installation.

## Première utilisation

Au premier lancement, va dans **Réglages** (icône en haut à droite de
l'écran d'accueil) et colle ta clé API Anthropic (la même que celle
utilisée pour l'appli de bureau, dans `~/.reelicious/.env`). Elle est
stockée chiffrée, uniquement sur le téléphone — jamais envoyée ailleurs
qu'à l'API Claude elle-même.

Ensuite, depuis l'écran d'accueil, touche **+**, colle un lien de reel
Instagram, et touche **Extraire la recette**.

## Ce qui diffère de l'appli de bureau (V1)

Cette première version mobile a un périmètre volontairement réduit, pour
livrer quelque chose d'installable et d'utilisable rapidement plutôt que
de tout construire d'un bloc :

- **Pas de transcription audio.** La reconstruction se base sur la
  légende du post et les images clés (texte incrusté à l'écran), comme
  côté bureau, mais sans la transcription de la voix. Techniquement, la
  bibliothèque utilisée côté bureau pour transcrire (`faster-whisper`)
  n'a pas de version compilée pour Android — il faudrait une bibliothèque
  distincte (`whisper.cpp`), nettement plus lourde à intégrer. La
  majorité des reels recette affichent déjà le texte à l'écran, donc
  l'impact reste limité en pratique ; si tu constates trop de recettes
  mal reconstruites (dictées à l'oral sans rien à l'écran), on l'ajoutera
  ensuite sans tout refaire.
- **Pas de calories** pour l'instant (ni affichage, ni estimation).
- **Pas d'export/import**, pas de réorganisation par glisser-déposer, pas
  de renommage de catégories — ces écrans existent côté bureau mais pas
  encore ici.

Le reste (titre, catégorie, portions, ingrédients, étapes, notes, image de
couverture, favoris, note sur 5 étoiles, saisie manuelle) fonctionne.

## Pourquoi pas de build automatique à chaque session de développement ?

Compiler une appli Android nécessite de télécharger le SDK Android
(`dl.google.com`), un service que mon environnement de développement
cloud ne peut pas atteindre (restriction réseau). Plutôt que de bloquer
dessus, le vrai assemblage de l'APK est délégué à GitHub Actions
(`.github/workflows/mobile-build.yml`), qui tourne sur des machines avec
un accès réseau complet. Chaque modification du code mobile déclenche
donc automatiquement une nouvelle compilation, consultable et
téléchargeable depuis l'onglet **Actions** du dépôt, sans que tu aies
besoin d'installer quoi que ce soit sur ton ordinateur.

## Pour les développeurs : structure du projet

```
mobile/android/
  app/src/main/
    java/com/reelicious/mobile/
      data/        modèle de domaine + Room (base SQLite locale) + clé API chiffrée
      network/     appel direct à l'API Claude (ClaudeClient)
      pipeline/     orchestration téléchargement -> images -> Claude (ExtractionPipeline),
                    extraction d'images clés native (FrameExtractor, sans ffmpeg)
      ui/           écrans Compose (accueil, ajout, relecture, détail, réglages)
    python/
      reelicious_download.py   wrapper yt-dlp, exécuté sur le téléphone via Chaquopy
                                (Python embarqué dans l'appli Android)
```

`engine/recipe_builder.py` (prompt Claude) et `engine/downloader.py` ont
servi de référence directe : le prompt système et la logique de
téléchargement sont volontairement les mêmes que côté bureau, pour que
les deux versions se comportent de façon cohérente.
