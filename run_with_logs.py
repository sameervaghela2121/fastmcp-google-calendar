#!/usr/bin/env python3
"""
MCP Server with Enhanced Logging
Run this script to see detailed logs from the MCP server
"""

import subprocess
import sys
import os
from pathlib import Path

def run_mcp_with_logs():
    """Run the MCP server with enhanced logging output."""
    
    # Set up environment
    current_dir = Path(__file__).parent
    venv_python = current_dir / "venv" / "bin" / "python"
    
    # Use virtual environment python if available
    python_cmd = str(venv_python) if venv_python.exists() else "python3"
    
    print("🚀 Starting Google Calendar MCP Server with Enhanced Logging")
    print("=" * 60)
    print(f"📁 Working Directory: {current_dir}")
    print(f"🐍 Python: {python_cmd}")
    print(f"🔧 Webhook URL: {os.environ.get('GOOGLE_CALENDAR_WEBHOOK_URL', 'Using default')}")
    print("=" * 60)
    print("📋 Server Logs:")
    print("-" * 60)
    
    try:
        # Run the server and capture output in real-time
        process = subprocess.Popen(
            [python_cmd, "run.py", "google-calendar"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print output in real-time
        for line in process.stdout:
            print(f"[MCP] {line.rstrip()}")
            
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
        process.terminate()
    except Exception as e:
        print(f"❌ Error running server: {e}")

if __name__ == "__main__":
    run_mcp_with_logs()
