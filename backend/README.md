# Live Comp Overlay Backend

Free, local-first Python backend that ingests Pokémon card data from TCGdex, computes CLIP image embeddings, and identifies cards uploaded from the iOS app.

## Stack

- **FastAPI** — HTTP API
- **SQLite** — local card/pricing database (swappable to PostgreSQL)
- **FAISS** — local vector similarity search (swappable to pgvector)
- **CLIP** (OpenAI `clip-vit-base-patch32`) — card image embeddings
- **Hugging Face Transformers + PyTorch**

## Setup (Windows)

Run the automated setup script. It downloads an embedded Python 3.11 into the project folder so you don't need to install Python system-wide.

```powershell
cd C:\Users\M\LiveCompOverlay\backend
.\setup.ps1
```

If you already have Python 3.11/3.12 installed, the script will use it instead.

## Run the server

```powershell
.\start_server.ps1
```

Or manually:

```powershell
venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server listens on `http://0.0.0.0:8000`. Use your PC's local IP in the iOS app (e.g., `http://192.168.1.100:8000`).

## Ingest cards

### Quick smoke test (one card)

Use this to test the iOS app immediately:

```powershell
venv\Scripts\Activate.ps1
python cli.py --smoke-test
```

### Ingest a few sets

```powershell
python cli.py 3
```

### Ingest all sets

```powershell
python cli.py
```

The first run downloads the CLIP model (~500 MB) and card images, so it may take a while. Subsequent runs use cached images and embeddings.

## API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Backend alive check |
| `/catalog/status` | GET | DB card count + FAISS index status |
| `/identify` | POST | Upload card image, get ranked matches |
| `/cards/search` | GET | Search cards by name/set/number |
| `/cards/{external_id}` | GET | Card details |

## Cloud migration

When you're ready to launch:

1. Deploy this folder to any VPS or container host.
2. Update `DATABASE_URL` to PostgreSQL + pgvector.
3. Swap FAISS for pgvector (optional).
4. Update the iOS app's **Backend URL** to your cloud host.

No app code changes required.
