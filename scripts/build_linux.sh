#!/usr/bin/env bash
set -euo pipefail
python3 -m pip install -r requirements-dev.txt
python3 -m PyInstaller --noconfirm --clean --windowed --name PocketForest --paths src src/forest_clone/main.py
printf 'Portable build ready: dist/PocketForest/PocketForest\n'

if command -v appimagetool >/dev/null 2>&1; then
  rm -rf AppDir
  mkdir -p AppDir/usr/lib AppDir/usr/bin AppDir/usr/share/applications \
    AppDir/usr/share/icons/hicolor/scalable/apps \
    AppDir/usr/share/icons/hicolor/256x256/apps
  cp -a dist/PocketForest AppDir/usr/lib/pocketforest
  cp assets/pocket-forest.svg AppDir/usr/share/icons/hicolor/scalable/apps/pocket-forest.svg
  cp assets/pocket-forest.png AppDir/usr/share/icons/hicolor/256x256/apps/pocket-forest.png
  cat > AppDir/usr/bin/pocket-forest <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/../lib/pocketforest/PocketForest" "$@"
EOF
  chmod +x AppDir/usr/bin/pocket-forest
  cat > AppDir/pocket-forest.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Pocket Forest
Exec=pocket-forest
Icon=pocket-forest
Categories=Utility;
Terminal=false
EOF
  cp AppDir/pocket-forest.desktop AppDir/usr/share/applications/
  cp assets/pocket-forest.png AppDir/pocket-forest.png
  ln -s pocket-forest.png AppDir/.DirIcon
  ln -s usr/bin/pocket-forest AppDir/AppRun
  runtime_cache="${XDG_CACHE_HOME:-$HOME/.cache}/pocket-forest/runtime-x86_64"
  if [[ ! -s "$runtime_cache" ]]; then
    mkdir -p "$(dirname "$runtime_cache")"
    curl --fail --location --retry 8 --retry-all-errors --retry-delay 3 \
      https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64 \
      --output "$runtime_cache"
  fi
  rm -f dist/PocketForest-x86_64.AppImage
  appimagetool --runtime-file "$runtime_cache" AppDir dist/PocketForest-x86_64.AppImage
  printf 'AppImage ready: dist/PocketForest-x86_64.AppImage\n'
else
  printf 'Optional AppImage skipped: appimagetool not found. Portable folder remains usable.\n'
fi
