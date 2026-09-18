# Python Version Requirement

The backend requires **Python 3.11 or 3.12**.

Python 3.14 (currently installed on this machine) is too new and does not have pre-built wheels for core ML dependencies such as NumPy, PyTorch, and older FAISS releases. Attempting to install on 3.14 will fail because pip tries to build these packages from source and a C compiler is not available.

## How to fix

1. Install Python 3.11 or 3.12 from https://www.python.org/downloads/
2. Verify the version:
   ```bash
   python3.11 --version
   ```
3. Recreate the virtual environment with the correct Python:
   ```bash
   cd C:\Users\M\LiveCompOverlay\backend
   Remove-Item -Recurse -Force venv
   py -3.11 -m venv venv
   venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

## Run the backend

```bash
venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Ingest catalog

```bash
venv\Scripts\Activate.ps1
python cli.py       # all sets
python cli.py 3     # first 3 sets only (for testing)
```
