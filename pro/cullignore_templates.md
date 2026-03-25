# .cullignore Templates

Drop a `.cullignore` file in the root directory you scan (e.g. `~/projects/.cullignore`).
Lines are matched against the cache directory name or its relative path.
Lines starting with `#` are comments.

---

## Node.js / JavaScript

```
# legacy app — keep node_modules (uses too many deprecated hooks)
legacy-app/node_modules

# monorepo root — don't touch the workspace node_modules
packages/*/node_modules

# build output we intentionally keep around
frontend/dist
```

---

## Python

```
# active virtualenv — don't delete while working
active-project/.venv

# shared tox env used across multiple runs
.tox

# type stubs we built manually
.mypy_cache/stubs
```

---

## Rust

```
# this build takes 20 min, leave it alone
slow-crate/target

# shared deps that took forever to compile
workspace/target/debug/deps
```

---

## Java / Maven / Gradle

```
# generated sources we version-control (shouldn't be here but it is)
legacy-service/target/generated-sources

# Android builds are slow, keep recent ones
android-app/.gradle
```

---

## .NET

```
# WPF project — designer cache is huge but needed
desktop-app/bin
desktop-app/obj
```

---

## General patterns

```
# skip anything in directories prefixed with "keep-"
keep-*/

# ignore all __pycache__ globally (if you prefer to manage them manually)
__pycache__

# skip caches in archived/reference projects
archive/*/node_modules
archive/*/.venv
```
