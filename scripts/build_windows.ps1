$ErrorActionPreference = "Stop"
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm --clean --windowed --name PocketForest --paths src src/forest_clone/main.py
Write-Host "Build ready: dist/PocketForest/PocketForest.exe"
