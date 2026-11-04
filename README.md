# Pocket Forest

Small offline desktop focus timer for Windows and Linux. Completed sessions plant trees, build history, and contribute to daily totals and streaks.

## Stack

Python 3.10+, PySide6, and SQLite from Python standard library. No browser, backend, account, network access, or database server. Timer uses absolute system-time deadlines; delayed UI updates do not change session duration. Active sessions recover after restart.

## Features

- Start, pause, resume, or cancel 15/25/45/60-minute and custom sessions
- Choose a peach or pine tree before each session; last planted species remains selected after restart
- Sessions under 30 minutes grow saplings; longer sessions scale to larger trees
- Each completed hour plants a grown tree; a remaining partial hour adds a sapling (90 minutes plants one grown tree and one sapling)
- Interrupted sessions leave one dead tree based on elapsed focus time
- Lightweight painted terrain and persistent forest
- Local chronological history and completion/interruption status
- Hover forest trees for species, session date/time, duration, result, and multi-tree origin
- Completed count, focused time, daily time, trees, and day streak
- Large foreground completion celebration with matching animated tree, alert sounds, View Forest, and Plant Another actions
- Compact non-modal interruption warning overlay
- Native background notification where system tray support exists
- Reward-aware messages describing species, grown trees, saplings, and withered trees
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

## UI structure

UI modules stay presentation-focused while `FocusController` owns timer/persistence coordination:

```text
src/forest_clone/ui/
├── main_window.py      # page orchestration and application actions
├── focus_view.py       # timer controls, preview, summary cards
├── forest_view.py      # period controls and terrain canvas
├── history_view.py     # session table
├── settings_view.py    # preference form
├── tree_painter.py     # shared peach/pine/sapling/dead rendering
├── theme.py            # application stylesheet
└── widgets.py          # small shared builders
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
