import sys

min_version = (3, 11)
max_version = (3, 13)
major, minor = sys.version_info[:2]

if major < min_version[0] or (major == min_version[0] and minor < min_version[1]):
    print(f"ERROR: Python {sys.version} is too old. Use Python 3.11 or 3.12.")
    sys.exit(1)

if (major, minor) >= max_version:
    print(f"ERROR: Python {sys.version} is too new. PyTorch/NumPy wheels are not available yet.")
    print("Install Python 3.11 or 3.12 from https://www.python.org/downloads/")
    sys.exit(1)

print(f"OK: Python {sys.version} is supported.")

required = [
    "fastapi",
    "uvicorn",
    "httpx",
    "PIL",
    "faiss",
    "torch",
    "transformers",
    "sqlalchemy",
]

missing = []
for module in required:
    try:
        __import__(module)
    except ImportError:
        missing.append(module)

if missing:
    print(f"ERROR: Missing dependencies: {', '.join(missing)}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

print("OK: All required dependencies are installed.")
