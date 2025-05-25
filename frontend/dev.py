#!/usr/bin/env python3
"""
Development script for Peloterm Vue UI.
Runs both the Vue dev server and FastAPI backend.
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path

def run_vue_dev():
    """Run the Vue development server."""
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

def run_fastapi_dev():
    """Run the FastAPI development server."""
    # Go up to the project root
    project_root = Path(__file__).parent.parent
    return subprocess.Popen(
        [sys.executable, "-m", "peloterm.web.server"],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

def main():
    print("🚴 Starting Peloterm Development Environment")
    print("=" * 50)
    
    vue_process = None
    fastapi_process = None
    
    try:
        # Start FastAPI server
        print("Starting FastAPI server on http://localhost:8000...")
        fastapi_process = run_fastapi_dev()
        time.sleep(2)  # Give it time to start
        
        # Start Vue dev server
        print("Starting Vue dev server on http://localhost:5173...")
        vue_process = run_vue_dev()
        time.sleep(3)  # Give it time to start
        
        print("\n✅ Development servers started!")
        print("📱 Vue UI: http://localhost:5173")
        print("🔌 FastAPI: http://localhost:8000")
        print("📊 API Config: http://localhost:8000/api/config")
        print("\nPress Ctrl+C to stop both servers")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if vue_process.poll() is not None:
                print("❌ Vue dev server stopped unexpectedly")
                break
            if fastapi_process.poll() is not None:
                print("❌ FastAPI server stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping development servers...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up processes
        if vue_process:
            vue_process.terminate()
            try:
                vue_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                vue_process.kill()
        
        if fastapi_process:
            fastapi_process.terminate()
            try:
                fastapi_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                fastapi_process.kill()
        
        print("✅ Development servers stopped")

if __name__ == "__main__":
    main() 