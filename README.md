# Reelicious

Application de bureau mono-utilisateur qui transforme un lien Instagram
(reel de recette) en fiche recette structurée : titre, portions,
ingrédients, étapes et image de couverture — plus une base locale pour
les retrouver.

## Pipeline d'extraction

1. **Téléchargement** de la vidéo (et de sa légende, souvent porteuse de
   la recette elle-même) via `yt-dlp`.
2. **Extraction de l'audio** en WAV mono 16 kHz via `ffmpeg`.
3. **Capture d'images clés**, réparties sur la durée de la vidéo, pour
   capter le texte incrusté à l'écran (ingrédients/quantités souvent
   affichés plutôt que dits).
4. **Transcription** de l'audio en local avec `faster-whisper` (aucun
   appel réseau à cette étape).
5. **Reconstruction de la recette** : un seul appel multimodal à Claude
   (texte + images) combine transcript, légende et images clés pour
   produire un JSON structuré (titre, portions, ingrédients, étapes).
6. **Image de couverture** : la miniature du post si disponible, sinon
   la première image clé extraite.

La vidéo source est conservée (pas seulement l'image de couverture) pour
pouvoir être rejouée depuis la fiche détail — voir la note sur l'espace
disque dans la Configuration ci-dessous.

Chaque étape peut échouer indépendamment sans faire échouer les autres :
le pipeline dégrade gracieusement (voir plus bas).

## Architecture

Le dépôt est découpé en trois packages Python, avec une règle stricte :
**seul `desktop/` a le droit de dépendre d'un toolkit d'interface.**

```
engine/     moteur d'extraction — aucune dépendance UI, aucune notion de
            stockage. Point d'entrée : ExtractionPipeline(config).extract(url)
storage/    persistance locale (SQLite) — aucune dépendance UI.
            Point d'entrée : RecipeRepository
desktop/    application de bureau (PySide6). Seul consommateur de engine+storage
            aujourd'hui.
tests/      tests de engine/ et storage/
```

Cette séparation existe pour une raison précise : une version mobile
avec serveur est prévue. Ce jour-là, un serveur (FastAPI ou autre)
importera directement `engine` et `storage` sans rien réécrire — il
remplacera `desktop` comme second consommateur, exactement comme
`desktop` est aujourd'hui le premier. `engine` et `storage` ne
connaissent d'ailleurs rien l'un de l'autre : c'est `storage` qui va
chercher les fichiers produits par `engine` (image de couverture) pour
les rendre durables, jamais l'inverse.

À l'intérieur de `engine`, chaque étape (téléchargement, transcription,
reconstruction LLM) est définie derrière une interface (`Protocol`)
avec une implémentation par défaut injectable — ça permet de tester
`ExtractionPipeline` sans réseau ni GPU, et de remplacer un composant
(un autre moteur de transcription, un autre fournisseur LLM) sans
toucher à l'orchestration.

### Dégradation gracieuse et mode de secours manuel

`ExtractionPipeline.extract()` renvoie toujours un `ExtractionResult`
exploitable, avec un statut :

- `SUCCESS` — recette complète reconstruite automatiquement.
- `PARTIAL` — la reconstruction automatique a échoué, mais transcript,
  légende et/ou images clés ont été récupérés : l'écran de saisie
  manuelle est pré-rempli avec ce qui est disponible plutôt que de
  repartir de zéro.
- `FAILED` — rien d'exploitable (typiquement le téléchargement a
  échoué) : l'utilisateur saisit la recette entièrement à la main.

Le mode manuel est aussi accessible directement depuis l'écran
d'accueil, sans passer par une tentative d'extraction.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[engine,desktop,dev]"
```

Il faut aussi `ffmpeg` sur le PATH (`apt install ffmpeg` / `brew install
ffmpeg`), et une clé `ANTHROPIC_API_KEY` (voir `.env.example`, à copier
en `.env`) pour la reconstruction automatique — sans clé, seul le mode
de saisie manuelle fonctionne.

## Lancer l'application

```bash
python -m desktop.app
```

## Construire un exécutable à double-cliquer

Pour éviter de repasser par le Terminal à chaque lancement :

```bash
# macOS
bash scripts/build_macos.sh      # produit dist/Reelicious.app

# Windows (PowerShell)
scripts\build_windows.ps1        # produit dist\Reelicious\Reelicious.exe
```

Ces scripts s'appuient sur PyInstaller (`pip install -e ".[build]"`) et
sur `scripts/generate_icon.py`, qui régénère `assets/icon.png` /
`assets/icon.ico` à partir des couleurs de `desktop/theme.py` — utile si
la charte visuelle change. La construction doit se faire sur le système
cible (un `.app` se construit sur Mac, un `.exe` sur Windows) : pas de
compilation croisée.

## Exporter / importer ses recettes

Depuis l'écran d'accueil, le menu **⋯** propose « Exporter mes
recettes… » et « Importer des recettes… ». L'export produit une
archive `.zip` autoportante (un manifeste JSON + les images de
couverture et les vidéos sources) — pour migrer vers un autre
ordinateur : exporter sur l'ancien poste, transférer le fichier (clé
USB, cloud, email), puis importer sur le nouveau. L'archive peut être
volumineuse (vidéos incluses). Réimporter une archive déjà importée met à
jour les recettes existantes plutôt que de les dupliquer (`storage/backup.py`).

## Configuration

Variables d'environnement (toutes optionnelles sauf `ANTHROPIC_API_KEY`
pour l'extraction automatique) :

| Variable | Défaut | Rôle |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Clé API pour la reconstruction de recette |
| `REELICIOUS_CLAUDE_MODEL` | `claude-sonnet-5` | Modèle utilisé |
| `REELICIOUS_WHISPER_SIZE` | `small` | Taille du modèle faster-whisper |
| `REELICIOUS_WHISPER_DEVICE` | `cpu` | `cpu` ou `cuda` |
| `REELICIOUS_DATA_DIR` | `~/.reelicious` | Vidéos/images/DB locale |
| `REELICIOUS_MAX_KEY_FRAMES` | `6` | Nombre d'images clés extraites |

> **Espace disque** : chaque recette conserve sa vidéo source (dans
> `REELICIOUS_DATA_DIR/videos`), en plus de son image de couverture, pour
> permettre de la rejouer depuis la fiche détail. Cela représente
> typiquement quelques dizaines de Mo par recette, contre quelques Ko
> auparavant.

## Tests

```bash
pytest
```

Les tests de `engine.audio` / `engine.frames` / `engine.pipeline`
génèrent une vidéo de test avec `ffmpeg` (aucun fichier binaire versionné,
aucun accès réseau) et font tourner l'extraction audio/images pour de
vrai ; le téléchargement, la transcription et l'appel LLM sont
injectés via de faux objets respectant les mêmes interfaces que les
implémentations réelles.
