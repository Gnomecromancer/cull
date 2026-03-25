"""
devcull TUI — interactive full-screen cache cleaner.
Requires: pip install devcull textual

Usage:
    python devcull_tui.py [path] [--older-than DAYS] [--min-size MB]
"""

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Label,
    ProgressBar,
    Static,
)
from textual.reactive import reactive
from textual import work

from cull.scan import scan, Hit


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _age_days(dt: datetime) -> int:
    return (datetime.now(tz=timezone.utc) - dt).days


def _age_str(days: int) -> str:
    if days > 365:
        return f"{days // 365}y"
    if days > 30:
        return f"{days // 30}mo"
    return f"{days}d"


class ScanStatus(Static):
    msg = reactive("ready")

    def render(self) -> str:
        return self.msg


class CullApp(App):
    TITLE = "devcull"
    CSS = """
    Screen {
        layout: vertical;
    }
    #toolbar {
        height: 3;
        background: $surface;
        padding: 0 2;
        layout: horizontal;
        align: left middle;
    }
    #status {
        padding: 0 2;
        color: $text-muted;
    }
    DataTable {
        height: 1fr;
    }
    #summary {
        height: 3;
        background: $surface;
        padding: 0 2;
        layout: horizontal;
        align: left middle;
    }
    #btn-delete {
        background: $error;
        color: white;
    }
    #btn-delete:hover {
        background: $error-darken-1;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_row", "Select"),
        Binding("a", "select_all", "All"),
        Binding("n", "select_none", "None"),
        Binding("d", "delete_selected", "Delete"),
        Binding("q", "quit", "Quit"),
        Binding("r", "rescan", "Rescan"),
    ]

    def __init__(self, root: Path, older_than: int, min_size_mb: int):
        super().__init__()
        self.root = Path(root)
        self.older_than = older_than
        self.min_size_mb = min_size_mb
        self.hits: list[Hit] = []
        self.selected: set[int] = set()  # indices into self.hits

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScanStatus(id="status")
        yield DataTable(id="table", cursor_type="row", zebra_stripes=True)
        with Horizontal(id="summary"):
            yield Label("", id="lbl-summary")
            yield Button("Delete selected", id="btn-delete", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        tbl.add_columns("", "Path", "Size", "Age", "Project")
        self.run_scan()

    @work(thread=True)
    def run_scan(self) -> None:
        status = self.query_one(ScanStatus)
        tbl = self.query_one(DataTable)

        self.call_from_thread(tbl.clear)
        self.selected.clear()
        self.hits = []

        def on_progress(p: Path):
            label = str(p)
            if len(label) > 70:
                label = "…" + label[-69:]
            self.call_from_thread(setattr, status, "msg", f"scanning {label}")

        all_hits = scan(self.root, progress_cb=on_progress)

        min_bytes = self.min_size_mb * 1024 * 1024
        self.hits = [
            h for h in all_hits
            if _age_days(h.last_used) >= self.older_than and h.size >= min_bytes
        ]

        def _populate():
            tbl.clear()
            for h in self.hits:
                proj_name = h.project.name if h.project else "—"
                tbl.add_row(
                    "☐",
                    str(h.path),
                    _fmt_size(h.size),
                    _age_str(_age_days(h.last_used)),
                    proj_name,
                )
            status.msg = (
                f"found {len(self.hits)} stale cache dirs  "
                f"({_fmt_size(sum(h.size for h in self.hits))})"
                if self.hits else "nothing stale found — you're clean"
            )
            self._refresh_summary()

        self.call_from_thread(_populate)

    def _refresh_summary(self) -> None:
        tbl = self.query_one(DataTable)
        lbl = self.query_one("#lbl-summary", Label)
        btn = self.query_one("#btn-delete", Button)

        if not self.selected:
            lbl.update("nothing selected")
            btn.disabled = True
            return

        sel_hits = [self.hits[i] for i in self.selected]
        total = sum(h.size for h in sel_hits)
        lbl.update(f"{len(sel_hits)} selected — {_fmt_size(total)}")
        btn.disabled = False

        # update checkboxes in table
        for row_i, h in enumerate(self.hits):
            mark = "☑" if row_i in self.selected else "☐"
            tbl.update_cell_at((row_i, 0), mark)

    def action_toggle_row(self) -> None:
        tbl = self.query_one(DataTable)
        row = tbl.cursor_row
        if row < 0 or row >= len(self.hits):
            return
        if row in self.selected:
            self.selected.discard(row)
        else:
            self.selected.add(row)
        self._refresh_summary()

    def action_select_all(self) -> None:
        self.selected = set(range(len(self.hits)))
        self._refresh_summary()

    def action_select_none(self) -> None:
        self.selected.clear()
        self._refresh_summary()

    def action_delete_selected(self) -> None:
        self._do_delete()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-delete":
            self._do_delete()

    @work(thread=True)
    def _do_delete(self) -> None:
        status = self.query_one(ScanStatus)
        to_del = sorted(self.selected, reverse=True)
        freed = 0
        for i in to_del:
            h = self.hits[i]
            self.call_from_thread(
                setattr, status, "msg", f"removing {h.path.name}…"
            )
            try:
                shutil.rmtree(h.path)
                freed += h.size
            except Exception as e:
                self.call_from_thread(
                    setattr, status, "msg", f"error: {e}"
                )
        self.call_from_thread(
            setattr, status, "msg",
            f"freed {_fmt_size(freed)} — rescanning…"
        )
        self.call_from_thread(self.run_scan)

    def action_rescan(self) -> None:
        self.run_scan()


def main():
    p = argparse.ArgumentParser(description="devcull TUI — interactive cache cleaner")
    p.add_argument("path", nargs="?", default=".", help="directory to scan (default: .)")
    p.add_argument("--older-than", type=int, default=90, metavar="DAYS")
    p.add_argument("--min-size", type=int, default=0, metavar="MB")
    args = p.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory")
        raise SystemExit(1)

    app = CullApp(root=root, older_than=args.older_than, min_size_mb=args.min_size)
    app.run()


if __name__ == "__main__":
    main()
