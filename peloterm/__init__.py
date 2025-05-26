"""Peloterm - A terminal-based cycling metrics visualization tool."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("peloterm")
except importlib.metadata.PackageNotFoundError:
    # Fallback for development when package is not installed
    __version__ = "0.1.0-dev" 