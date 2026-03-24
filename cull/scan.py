import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# directories that are definitely just build/cache garbage
CACHE_DIRS = {
    "node_modules",
    ".venv", "venv", ".virtualenv",
    ".next", ".nuxt", ".svelte-kit", ".solid",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox",
    "dist", "build", "out",
    ".parcel-cache", ".turbo", ".sass-cache",
    ".gradle", ".gradle-cache",
    ".angular",
}

# only count these as cache if there's a project marker nearby
# (don't nuke a top-level "target" folder that could be anything)
CONDITIONAL = {
    "target",  # rust/maven — check for Cargo.toml or pom.xml
}

PROJECT_MARKERS = {
    "package.json", "Cargo.toml", "pom.xml", "pyproject.toml",
    "setup.py", "go.mod", "build.gradle", ".git",
}


@dataclass
class Hit:
    path: Path
    size: int = 0           # bytes
    last_used: datetime = field(default_factory=lambda: datetime.min.replace(tzinfo=timezone.utc))
    project: Path | None = None


def _project_root(p: Path) -> Path | None:
    """walk up from p looking for a project marker"""
    cur = p.parent
    for _ in range(6):  # don't walk forever
        if any((cur / m).exists() for m in PROJECT_MARKERS):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _dir_size(p: Path) -> int:
    total = 0
    # os.scandir is faster than os.walk for shallow trees,
    # but node_modules can be 8 levels deep so we walk
    try:
        for entry in os.scandir(p):
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                total += _dir_size(Path(entry.path))
            else:
                try:
                    total += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    pass
    except PermissionError:
        pass
    return total


def _last_git_commit(project: Path) -> datetime | None:
    # git log is slow but mtime lies on windows (copying a file updates mtime)
    try:
        r = subprocess.run(
            ["git", "-C", str(project), "log", "-1", "--format=%ct"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            ts = int(r.stdout.strip())
            return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        pass
    return None


def _last_used(hit_path: Path, project: Path | None) -> datetime:
    if project:
        t = _last_git_commit(project)
        if t:
            return t
    # fall back to the mtime of the cache dir itself
    try:
        st = hit_path.stat()
        return datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
    except OSError:
        return datetime.min.replace(tzinfo=timezone.utc)


def scan(root: Path, progress_cb=None) -> list[Hit]:
    """
    Walk root looking for cache directories. Doesn't recurse into found dirs.
    progress_cb(path) is called as we enter each directory, for spinner updates.
    """
    hits = []
    # TODO: handle junction points (windows symlink variant)

    for dirpath, dirnames, _ in os.walk(root, topdown=True, onerror=None, followlinks=False):
        p = Path(dirpath)

        if progress_cb:
            progress_cb(p)

        # prune dirs we should never descend into
        prune = []
        for d in dirnames:
            if d.startswith(".git") and d != ".git":
                prune.append(d)
                continue

            if d in CACHE_DIRS:
                full = p / d
                proj = _project_root(full)
                h = Hit(path=full, project=proj)
                hits.append(h)
                prune.append(d)
                continue

            if d in CONDITIONAL:
                # only include 'target' if a build marker is in the immediate parent
                if (p / "Cargo.toml").exists() or (p / "pom.xml").exists():
                    full = p / d
                    hits.append(Hit(path=full, project=p))
                    prune.append(d)

        for d in prune:
            dirnames.remove(d)

    # fill in sizes + last-used after the walk so the spinner can run cleanly
    for h in hits:
        h.size = _dir_size(h.path)
        h.last_used = _last_used(h.path, h.project)

    return hits
