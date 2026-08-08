"""
ingest.py

Manual re-indexing script. Run this any time you want to (re)process every
PDF in the `documents/` folder into ChromaDB by hand:

    python ingest.py

The actual extraction/chunking/embedding logic lives in ingest_service.py
now (so the API can call the exact same code automatically after an
upload), but the behavior here is identical to before.
"""

from ingest_service import run_ingestion

if __name__ == "__main__":
    run_ingestion()
