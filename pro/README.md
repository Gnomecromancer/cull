# devcull Pro Pack

Thanks for buying the pro pack. This is the "set it and forget it" layer on top of
the free `devcull` tool — scheduled weekly cleaning with a notification when space is freed,
plus `.cullignore` templates so you're never deleting something you didn't mean to.

## What's in here

| File | What it does |
|---|---|
| `devcull_tui.py` | Full-screen interactive TUI — browse and select caches with mouse/keyboard |
| `setup_weekly_clean_windows.ps1` | Registers a weekly Task Scheduler job |
| `setup_weekly_clean_unix.sh` | Adds a weekly cron job on macOS/Linux |
| `notify_on_clean.ps1` | Runs cull and shows a Windows toast with the result |
| `cullignore_templates.md` | `.cullignore` examples for Node, Python, Rust, Java, .NET |

## The TUI

```
pip install devcull textual
python devcull_tui.py ~/projects
```

Full-screen terminal UI. Space to select rows, `a` for all, `d` to delete,
`r` to rescan, `q` to quit. Works on Windows (Windows Terminal), macOS, Linux.

## Quick start (Windows, scheduled cleaning)

1. Install devcull: `pip install devcull`
2. Open PowerShell as admin and run:
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\setup_weekly_clean_windows.ps1 -Path C:\your\projects
   ```
3. Done. Every Sunday at 9am, stale caches get cleaned silently.

For the toast notification version (recommended), use `notify_on_clean.ps1` as the
task action instead. See comments at the top of that file.

## Quick start (macOS/Linux)

1. Install devcull: `pip install devcull`
2. Run:
   ```bash
   chmod +x setup_weekly_clean_unix.sh
   ./setup_weekly_clean_unix.sh ~/projects 90
   ```
3. Done. Runs every Sunday at 9am, logs to `~/.cull.log`.

## Customizing what gets ignored

Copy the relevant section from `cullignore_templates.md` into a `.cullignore` file
in your projects root. devcull reads it automatically on every scan.

## Updates

The free `devcull` package gets updates via `pip install --upgrade devcull`.
The pro pack scripts don't need updates — they call `cull` which updates with pip.

---

Questions? gnomecromancer@proton.me
