#!/usr/bin/env python3
"""
Development script for PeloTerm.
Provides easy access to development and production modes.
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path

def run_vue_dev():
    """Run the Vue development server."""
    frontend_dir = Path(__file__).parent / "frontend"
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir
    )

def run_fastapi_dev():
    """Run the FastAPI development server."""
    return subprocess.Popen(
        [sys.executable, "-m", "peloterm.web.server"],
        cwd=Path(__file__).parent
    )

def dev_mode():
    """Run both Vue dev server and FastAPI for development."""
    print("🚴 Starting PeloTerm Development Environment")
    print("=" * 50)
    
    vue_process = None
    fastapi_process = None
    
    try:
        # Start FastAPI server
        print("Starting FastAPI server on http://localhost:8000...")
        fastapi_process = run_fastapi_dev()
        time.sleep(2)
        
        # Start Vue dev server
        print("Starting Vue dev server on http://localhost:5173...")
        vue_process = run_vue_dev()
        time.sleep(3)
        
        print("\n✅ Development servers started!")
        print("📱 Vue UI: http://localhost:5173")
        print("🔌 FastAPI: http://localhost:8000")
        print("📊 API Config: http://localhost:8000/api/config")
        print("\nPress Ctrl+C to stop both servers")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
            if vue_process.poll() is not None:
                print("❌ Vue dev server stopped unexpectedly")
                break
            if fastapi_process.poll() is not None:
                print("❌ FastAPI server stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping development servers...")
    finally:
        if vue_process:
            vue_process.terminate()
        if fastapi_process:
            fastapi_process.terminate()
        print("✅ Development servers stopped")

def prod_mode():
    """Run production server with built Vue files."""
    print("🚴 Starting PeloTerm Production Server")
    print("=" * 40)
    
    # Check if built files exist
    static_dir = Path(__file__).parent / "peloterm" / "web" / "static"
    if not (static_dir / "index.html").exists():
        print("❌ No built frontend found. Run 'python build.py' first.")
        sys.exit(1)
    
    print("🚀 Starting production server on http://localhost:8000...")
    try:
        subprocess.run([sys.executable, "-m", "peloterm.web.server"])
    except KeyboardInterrupt:
        print("\n✅ Production server stopped")

def main():
    parser = argparse.ArgumentParser(description="PeloTerm Development Script")
    parser.add_argument(
        "mode", 
        choices=["dev", "prod"], 
        nargs="?", 
        default="dev",
        help="Run in development or production mode (default: dev)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "dev":
        dev_mode()
    else:
        prod_mode()

if __name__ == "__main__":
    main() 