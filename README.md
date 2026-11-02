# Pocket Forest

Small offline desktop focus timer for Windows and Linux. Completed sessions plant trees, build history, and contribute to daily totals and streaks.

## Stack

Python 3.10+, PySide6, and SQLite from Python standard library. No browser, backend, account, network access, or database server. Timer uses absolute system-time deadlines; delayed UI updates do not change session duration. Active sessions recover after restart.

## Features

- Start, pause, resume, or cancel 15/25/45/60-minute and custom sessions
- Lightweight painted tree and persistent forest
- Local chronological history and completion/interruption status
- Completed count, focused time, daily time, trees, and day streak
- Native completion notification where system tray support exists
- System, light, and dark themes
- SQLite data under OS application-data directory

## Development

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python -m forest_clone
```

Linux needs common Qt desktop libraries supplied by most desktop distributions. App works fully offline after installation.

Run logic tests without requiring Qt:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

PowerShell:

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests -v
```

## Distribution

Build on each target OS; PyInstaller output is platform-specific.

### Windows

```powershell
.\scripts\build_windows.ps1
```

Distribute `dist\PocketForest\` as portable folder. Launch `PocketForest.exe`. Folder mode starts faster than one-file packaging and requires no installed Python.

### Linux

```bash
chmod +x scripts/build_linux.sh
./scripts/build_linux.sh
```

Distribute `dist/PocketForest/` as portable folder. Launch `PocketForest`. If `appimagetool` is on `PATH`, script also creates `dist/PocketForest-x86_64.AppImage`; otherwise it skips that optional step. AppImage portability depends on building on an older compatible Linux distribution; test on each supported distribution.

## GitHub Actions builds

Workflow `.github/workflows/build.yml` builds both platforms on GitHub-hosted runners. It runs manually and for tags beginning with `v`.

Manual build:

1. Push repository to GitHub.
2. Open **Actions** → **Build desktop bundles**.
3. Select **Run workflow** → **Run workflow**.
4. Wait for both jobs to finish.
5. Download artifacts from workflow summary:
   - `PocketForest-windows-x86_64`
   - `PocketForest-linux-x86_64`

Downloaded GitHub artifacts are ZIP files. Extract Windows artifact fully before launching `PocketForest.exe`; bundled `_internal` files must stay beside executable. Linux artifact contains executable AppImage.

Tag-triggered build:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Workflow uses Ubuntu 22.04 for better Linux compatibility than building on newer workstation. It retains artifacts for 14 days to limit storage use. Public repositories normally receive free standard-runner Actions usage. Private repositories use plan-specific included minutes and storage; check GitHub **Settings → Billing and licensing → Usage** for current allowance.

## Data and recovery

Database path comes from Qt `AppDataLocation` (`%LOCALAPPDATA%/PocketForest` on typical Windows installs and `~/.local/share/PocketForest` on typical Linux installs). Running sessions store deadline; paused sessions store exact remaining duration. Restart finalizes sessions whose deadline elapsed. SQLite WAL and transactions protect writes after unexpected shutdowns.

## Scope

No cloud sync, accounts, social features, background service, analytics, or network calls. Closing app stops process; active timer state remains recoverable.

## License

MIT
