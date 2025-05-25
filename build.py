#!/usr/bin/env python3
"""
Build script for PeloTerm.
Builds the Vue frontend and prepares the Python package.
"""

import subprocess
import sys
import shutil
from pathlib import Path

def build_frontend():
    """Build the Vue frontend."""
    print("🏗️  Building Vue frontend...")
    
    frontend_dir = Path(__file__).parent / "frontend"
    
    # Install dependencies if node_modules doesn't exist
    if not (frontend_dir / "node_modules").exists():
        print("📦 Installing frontend dependencies...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    
    # Build the frontend
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Frontend build failed: {result.stderr}")
        return False
    
    print("✅ Frontend built successfully!")
    return True

def build_python_package():
    """Build the Python package distributions."""
    print("📦 Building Python package...")
    
    # Clean previous dist
    dist_dir = Path(__file__).parent / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()
    
    # Install hatchling if not available
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "hatchling"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Failed to install hatchling: {result.stderr}")
        return False
    
    # Build wheel using hatchling directly
    result = subprocess.run(
        [sys.executable, "-m", "hatchling", "build"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Python package build failed: {result.stderr}")
        return False
    
    print("✅ Python package built successfully!")
    return True

def verify_build():
    """Verify that the build output exists."""
    static_dir = Path(__file__).parent / "peloterm" / "web" / "static"
    index_file = static_dir / "index.html"
    
    if not index_file.exists():
        print("❌ Build verification failed: index.html not found")
        return False
    
    assets_dir = static_dir / "assets"
    if not assets_dir.exists() or not any(assets_dir.iterdir()):
        print("❌ Build verification failed: assets directory empty")
        return False
    
    print("✅ Build verification passed!")
    return True

def clean_build():
    """Clean previous build artifacts."""
    static_dir = Path(__file__).parent / "peloterm" / "web" / "static"
    
    if static_dir.exists():
        print("🧹 Cleaning previous build...")
        # Keep the original index.html as backup
        original_index = static_dir / "index.html.original"
        current_index = static_dir / "index.html"
        
        # Backup original if it doesn't exist and current does
        if current_index.exists() and not original_index.exists():
            # Only backup if it looks like the original (very large file)
            if current_index.stat().st_size > 10000:  # Original was 20KB+
                shutil.copy2(current_index, original_index)
        
        # Remove all files except the backup
        for item in static_dir.iterdir():
            if item.name != "index.html.original":
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

def main():
    """Main build process."""
    print("🚴 PeloTerm Build Process")
    print("=" * 30)
    
    try:
        # Clean previous build
        clean_build()
        
        # Build frontend
        if not build_frontend():
            sys.exit(1)
        
        # Build Python package
        if not build_python_package():
            sys.exit(1)
        
        # Verify build
        if not verify_build():
            sys.exit(1)
        
        print("\n🎉 Build completed successfully!")
        print("📦 Static files are ready in: peloterm/web/static/")
        print("📦 Python package distributions are in: dist/")
        print("🚀 You can now run: python -m peloterm.web.server")
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 