# graph-engineering

## Setup with uv

Create/sync the local environment:

```powershell
uv sync
```

Run a Python script:

```powershell
uv run python path\to\script.py
```

Start JupyterLab:

```powershell
uv run jupyter lab
```

In VS Code, open a notebook and select the Python interpreter at
`.venv\Scripts\python.exe` as its kernel.

Add another runtime dependency with `uv add <package>`, or a development-only
dependency with `uv add --dev <package>`.
