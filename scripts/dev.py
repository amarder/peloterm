#!/usr/bin/env python3
"""
Development script for Peloterm.
Provides easy access to development and production modes.
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path

def run_vue_dev():
    """Run the Vue development server."""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir
    )

def run_fastapi_dev():
    """Run the FastAPI development server."""
    return subprocess.Popen(
        [sys.executable, "-m", "peloterm.web.server"],
        cwd=Path(__file__).parent.parent
    )

def dev_mode():
    """Run both Vue dev server and FastAPI for development."""
    print("🚴 Starting Peloterm Development Environment")
    print("=" * 50)
    
    vue_process = None
    
    try:
        # Start Vue dev server
        print("Starting Vue dev server on http://localhost:5173...")
        vue_process = run_vue_dev()
        time.sleep(3)
        
        print("\n✅ Development servers starting!")
        print("📱 Vue UI: http://localhost:5173 (or check console for actual port)")
        print("🔌 FastAPI: http://localhost:8000")
        print("📊 API Config: http://localhost:8000/api/config")
        print("🚴 Mock devices enabled for development")
        print("\nPress Ctrl+C to stop both servers")
        
        # Start FastAPI server with integrated mock data generation
        # This runs in the main thread so globals work properly
        from peloterm.web.server import start_server_with_mock_data
        start_server_with_mock_data(port=8000, ride_duration_minutes=30)
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping development servers...")
    finally:
        if vue_process:
            vue_process.terminate()
        print("✅ Development servers stopped")

def prod_mode():
    """Run production server with built Vue files."""
    print("🚴 Starting Peloterm Production Server")
    print("=" * 40)
    
    # Check if built files exist
    static_dir = Path(__file__).parent.parent / "peloterm" / "web" / "static"
    if not (static_dir / "index.html").exists():
        print("❌ No built frontend found. Run 'python build.py' first.")
        sys.exit(1)
    
    print("🚀 Starting production server on http://localhost:8000...")
    try:
        subprocess.run([sys.executable, "-m", "peloterm.web.server"])
    except KeyboardInterrupt:
        print("\n✅ Production server stopped")

def main():
    parser = argparse.ArgumentParser(description="Peloterm Development Script")
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