#!/usr/bin/env python3
"""Sentinel AI — Unified Application Launcher.

Starts the FastAPI backend with the React production build served from
a single URL.

Usage:
    python scripts/start.py              # Production mode (port 8000)
    python scripts/start.py --dev        # Development mode (API 8000 + Vite 5173)
    python scripts/start.py --port 3000  # Custom port
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"


def _build_frontend() -> bool:
    """Build the React frontend if the dist folder doesn't exist."""
    if DIST.is_dir() and (DIST / "index.html").is_file():
        print("✓ React build found at frontend/dist")
        return True

    print("⟳ Building React frontend...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(FRONTEND),
        shell=True,
    )
    if result.returncode != 0:
        print("✗ Frontend build failed. Check errors above.")
        return False
    print("✓ Frontend built successfully")
    return True


def start_production(port: int = 8000) -> None:
    """Start the unified server (API + React SPA from a single port)."""
    if not _build_frontend():
        sys.exit(1)

    print()
    print("━" * 56)
    print("  SENTINEL AI — Unified Application")
    print("━" * 56)
    print(f"  ➜  Application:  http://localhost:{port}")
    print(f"  ➜  API Docs:     http://localhost:{port}/api/docs")
    print(f"  ➜  Health:       http://localhost:{port}/api/health")
    print()
    print("  Streamlit fallback is available separately via:")
    print("     streamlit run app.py --server.port 8501")
    print("━" * 56)
    print()

    os.chdir(str(ROOT))
    subprocess.run(
        [
            sys.executable, "-m", "uvicorn",
            "api.main:app",
            "--host", "0.0.0.0",
            "--port", str(port),
        ],
    )


def start_development(port: int = 8000) -> None:
    """Start both the API server (with --reload) and the Vite dev server."""
    print()
    print("━" * 56)
    print("  SENTINEL AI — Development Mode")
    print("━" * 56)
    print(f"  ➜  React (HMR):  http://localhost:5173")
    print(f"  ➜  API Server:   http://localhost:{port}")
    print(f"  ➜  API Docs:     http://localhost:{port}/api/docs")
    print()
    print("  Press Ctrl+C to stop all processes.")
    print("━" * 56)
    print()

    os.chdir(str(ROOT))

    # Start FastAPI with reload
    api_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "api.main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", str(port),
        ],
    )

    # Start Vite dev server
    vite_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(FRONTEND),
        shell=True,
    )

    try:
        # Wait for either to exit
        while True:
            if api_proc.poll() is not None:
                print("\nAPI server exited.")
                break
            if vite_proc.poll() is not None:
                print("\nVite dev server exited.")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        api_proc.terminate()
        vite_proc.terminate()
        api_proc.wait(timeout=5)
        vite_proc.wait(timeout=5)
        print("All processes stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel AI Unified Launcher")
    parser.add_argument(
        "--dev", action="store_true",
        help="Start in development mode (API + Vite HMR)",
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", 8000)),
        help="Port for the API/unified server (default: $PORT or 8000)",
    )
    args = parser.parse_args()

    if args.dev:
        start_development(args.port)
    else:
        start_production(args.port)


if __name__ == "__main__":
    main()
