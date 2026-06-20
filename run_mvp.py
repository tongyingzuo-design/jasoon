from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor" / "python"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    args = parser.parse_args()
    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        reload=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()
