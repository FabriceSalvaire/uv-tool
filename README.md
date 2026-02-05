This repository contains a Python script to show package sizes and versions of an [uv](https://docs.astral.sh/uv/concepts/cache) cache.

Package manager like `uv` or `pnpm` are great to isolate efficiently environments.  However it doesn't solve the
disk space lost by unused projects.

**Idea for new features:**
- find all `.venv` on disk
- find which `.venv` require a (outdated) package
- find potential unused `.venv` to avoid to accumulate on disk many outdated packages...
- mass update for outdated packages (usually Python packages doesn't break like for Node...)
