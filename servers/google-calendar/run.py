#!/usr/bin/env python3
"""
Google Calendar MCP Server Runner

Simple script to run the Google Calendar MCP server.
Usage: python run.py
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Add shared utilities to Python path
shared_src_dir = current_dir.parent.parent / "shared" / "src"
sys.path.insert(0, str(shared_src_dir))

# Check if running in virtual environment, if not try to activate it
venv_path = current_dir.parent.parent / "venv"
if venv_path.exists() and "VIRTUAL_ENV" not in os.environ:
    # Add virtual environment packages to path
    venv_site_packages = venv_path / "lib" / "python3.13" / "site-packages"
    if venv_site_packages.exists():
        sys.path.insert(0, str(venv_site_packages))

# Import and run the main function
from main import main

if __name__ == "__main__":
    print("🚀 Starting Google Calendar MCP Server...")
    print(f"📁 Working directory: {current_dir}")
    print(f"🔧 Webhook URL: {os.environ.get('GOOGLE_CALENDAR_WEBHOOK_URL', 'Using default')}")
    print("-" * 50)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
