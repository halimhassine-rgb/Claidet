# Construit Reelicious.exe (Windows uniquement) : a lancer depuis un
# PowerShell dans lequel l'environnement virtuel du projet est deja
# active (voir le guide d'installation). Resultat : dist\Reelicious\Reelicious.exe
Set-Location (Split-Path $PSScriptRoot -Parent)
$ErrorActionPreference = "Stop"

Write-Host "Installation des outils de build..."
pip install -q -e ".[build]"

Write-Host "Generation de l'icone..."
python scripts\generate_icon.py

Write-Host "Nettoyage des anciennes constructions (evite de garder un .exe perime)..."
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Host "Empaquetage avec PyInstaller (ca prend quelques minutes)..."
pyinstaller --name Reelicious --windowed --noconfirm `
  --icon assets\icon.ico `
  --add-data "assets;assets" `
  --collect-all faster_whisper `
  --collect-all ctranslate2 `
  --collect-all yt_dlp `
  --collect-all PySide6.QtMultimedia `
  --collect-all PySide6.QtMultimediaWidgets `
  desktop\app.py

if ($LASTEXITCODE -ne 0 -or -not (Test-Path "dist\Reelicious\Reelicious.exe")) {
    Write-Host ""
    Write-Host "ECHEC : PyInstaller n'a pas produit dist\Reelicious\Reelicious.exe." -ForegroundColor Red
    Write-Host "Faites defiler vers le haut pour trouver le message d'erreur exact" -ForegroundColor Red
    Write-Host "(souvent bloque par l'antivirus/Windows Defender, ou une dependance manquante)." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Termine : dist\Reelicious\Reelicious.exe"
Write-Host "Faites un clic droit dessus -> Envoyer vers -> Bureau (creer un raccourci) pour l'avoir en icone sur le Bureau."
