import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from cull import __version__
from cull.scan import scan, Hit


console = Console()


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _age_days(dt: datetime) -> int:
    now = datetime.now(tz=timezone.utc)
    return (now - dt).days


def _delete(h: Hit):
    try:
        shutil.rmtree(h.path)
        return True
    except Exception as e:
        console.print(f"  [red]couldn't remove {h.path.name}: {e}[/red]")
        return False


def _show_table(hits: list[Hit]):
    t = Table(show_header=True, header_style="bold", box=None, pad_edge=False, show_edge=False)
    t.add_column("#", style="dim", width=4)
    t.add_column("path", no_wrap=False, max_width=60)
    t.add_column("size", justify="right", style="yellow")
    t.add_column("last commit", justify="right", style="cyan")

    for i, h in enumerate(hits, 1):
        age = _age_days(h.last_used)
        if age > 365:
            age_str = f"{age // 365}y ago"
        elif age > 30:
            age_str = f"{age // 30}mo ago"
        else:
            age_str = f"{age}d ago"

        t.add_row(
            str(i),
            str(h.path),
            _fmt_size(h.size),
            age_str,
        )

    console.print(t)


@click.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--older-than", default=90, metavar="DAYS",
              help="only show caches not touched in N days (default: 90)")
@click.option("--min-size", default=0, metavar="MB",
              help="only show caches larger than N megabytes")
@click.option("--delete", is_flag=True, help="interactively delete found caches")
@click.option("--all", "delete_all", is_flag=True, help="delete everything without asking (use with care)")
@click.option("--dry-run", is_flag=True, help="show what would be deleted but don't touch anything")
@click.option("--report", "report_file", default=None, metavar="FILE",
              help="write findings to a JSON file")
@click.version_option(__version__, prog_name="cull")
def cli(path, older_than, min_size, delete, delete_all, dry_run, report_file):
    """Find and remove stale dev cache directories.

    Scans PATH (default: current directory) for node_modules, .venv,
    __pycache__, and similar directories that are safe to delete.
    """
    root = Path(path).resolve()

    hits: list[Hit] = []

    with console.status(f"scanning [dim]{root}[/dim]...", spinner="dots") as status:
        def on_progress(p: Path):
            # trim the path so it doesn't wrap
            label = str(p)
            if len(label) > 60:
                label = "..." + label[-57:]
            status.update(f"scanning [dim]{label}[/dim]")

        hits = scan(root, progress_cb=on_progress)

    if not hits:
        rprint("[green]nothing found, you're clean[/green]")
        return

    # filter by age and size
    min_bytes = min_size * 1024 * 1024
    filtered = [h for h in hits if _age_days(h.last_used) >= older_than and h.size >= min_bytes]

    if not filtered:
        qualifier = f"touched in the last {older_than} days"
        if min_size:
            qualifier += f" or smaller than {min_size} MB"
        rprint(f"[green]found {len(hits)} cache dirs but none match your filters ({qualifier})[/green]")
        return

    total = sum(h.size for h in filtered)
    rprint(f"\nfound [bold]{len(filtered)}[/bold] stale cache dirs totaling [yellow bold]{_fmt_size(total)}[/yellow bold]\n")
    _show_table(filtered)

    if report_file:
        data = {
            "scanned": str(root),
            "at": datetime.now(tz=timezone.utc).isoformat(),
            "filters": {"older_than_days": older_than, "min_size_mb": min_size},
            "hits": [
                {
                    "path": str(h.path),
                    "size_bytes": h.size,
                    "last_used": h.last_used.isoformat(),
                    "project": str(h.project) if h.project else None,
                }
                for h in filtered
            ],
        }
        Path(report_file).write_text(json.dumps(data, indent=2), encoding="utf-8")
        rprint(f"[dim]report saved → {report_file}[/dim]")

    if dry_run:
        rprint("\n[dim](dry run — nothing deleted)[/dim]")
        return

    if not delete and not delete_all:
        return

    print()

    if delete_all:
        if not click.confirm(f"delete all {len(filtered)} dirs ({_fmt_size(total)})?"):
            return
        removed = freed = 0
        for h in filtered:
            if _delete(h):
                freed += h.size
                removed += 1
        rprint(f"\n[green]removed {removed} dirs, freed {_fmt_size(freed)}[/green]")
        return

    # interactive mode
    rprint("[dim]enter numbers to delete (e.g. 1 3 5), 'a' for all, or q to quit[/dim]\n")
    while True:
        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if raw in ("q", "quit", ""):
            break

        if raw == "a":
            chosen = filtered
        else:
            indices = []
            valid = True
            for tok in raw.split():
                try:
                    n = int(tok)
                    if 1 <= n <= len(filtered):
                        indices.append(n - 1)
                    else:
                        rprint(f"[red]{n} is out of range[/red]")
                        valid = False
                        break
                except ValueError:
                    rprint(f"[red]'{tok}' isn't a number[/red]")
                    valid = False
                    break
            if not valid:
                continue
            chosen = [filtered[i] for i in indices]

        if not chosen:
            continue

        sz = sum(h.size for h in chosen)
        if not click.confirm(f"delete {len(chosen)} dir(s) ({_fmt_size(sz)})?"):
            continue

        removed = freed = 0
        for h in chosen:
            console.print(f"  removing [dim]{h.path}[/dim]...", end=" ")
            if _delete(h):
                freed += h.size
                removed += 1
                console.print("[green]done[/green]")
            # remove from list so 'a' doesn't re-select deleted entries
            filtered = [x for x in filtered if x.path != h.path]

        rprint(f"[green]freed {_fmt_size(freed)}[/green]")

        if not filtered:
            rprint("[green]nothing left[/green]")
            break

        # reprint table with updated indices
        print()
        _show_table(filtered)
        print()
