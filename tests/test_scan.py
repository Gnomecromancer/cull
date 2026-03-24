import os
import tempfile
from pathlib import Path
from datetime import timezone

from cull.scan import scan, CACHE_DIRS


def _make_tree(base: Path, structure: dict):
    for name, children in structure.items():
        p = base / name
        if children is None:
            p.touch()
        else:
            p.mkdir(parents=True, exist_ok=True)
            _make_tree(p, children)


def test_finds_node_modules():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root, {
            "my-project": {
                "package.json": None,
                "src": {"index.js": None},
                "node_modules": {
                    "lodash": {"index.js": None},
                },
            }
        })
        hits = scan(root)
        names = [h.path.name for h in hits]
        assert "node_modules" in names


def test_doesnt_recurse_into_found():
    # if node_modules contains another node_modules, we should only report
    # the outer one
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root, {
            "project": {
                "package.json": None,
                "node_modules": {
                    "some-pkg": {
                        "node_modules": {"deep.js": None},
                    }
                },
            }
        })
        hits = scan(root)
        assert len(hits) == 1
        assert hits[0].path.name == "node_modules"


def test_skips_recent_when_filtered(tmp_path):
    _make_tree(tmp_path, {
        "proj": {
            "pyproject.toml": None,
            ".pytest_cache": {"v": {"cache": {"lastfailed": None}}},
        }
    })
    hits = scan(tmp_path)
    # just check we found it — age filtering is in cli
    assert any(h.path.name == ".pytest_cache" for h in hits)


def test_cullignore_skips_matching_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root, {
            "app1": {"package.json": None, "node_modules": {"react": {"index.js": None}}},
            "app2": {"package.json": None, "node_modules": {"vue": {"index.js": None}}},
        })
        # ignore app1's node_modules
        (root / ".cullignore").write_text("app1/node_modules\n")
        hits = scan(root)
        paths = [str(h.path.relative_to(root)).replace("\\", "/") for h in hits]
        assert "app2/node_modules" in paths
        assert "app1/node_modules" not in paths


def test_conditional_target_with_cargo():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root, {
            "rust-proj": {
                "Cargo.toml": None,
                "src": {"main.rs": None},
                "target": {"debug": {"app.exe": None}},
            },
            "random-dir": {
                "target": {"something.txt": None},  # no marker — should be ignored
            },
        })
        hits = scan(root)
        names = [h.path.name for h in hits]
        # target inside rust project: yes. target with no marker: no.
        assert names.count("target") == 1
