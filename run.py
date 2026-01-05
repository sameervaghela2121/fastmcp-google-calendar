#!/usr/bin/env python3
"""
Chime Labs MCP Servers Runner

Central runner script for all MCP servers in the monorepo.
Usage: 
    python run.py                    # Show available servers
    python run.py google-calendar    # Run Google Calendar server
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List

# Available servers configuration
SERVERS = {
    "google-calendar": {
        "name": "Google Calendar MCP Server",
        "path": "servers/google-calendar",
        "script": "run.py",
        "description": "Calendar integration with availability checking and appointment booking"
    }
}

def show_help():
    """Display available servers and usage information."""
    print("🔧 Chime Labs MCP Servers")
    print("=" * 50)
    print("\nAvailable servers:")
    
    for server_id, config in SERVERS.items():
        print(f"\n📋 {server_id}")
        print(f"   Name: {config['name']}")
        print(f"   Description: {config['description']}")
        print(f"   Path: {config['path']}")
    
    print(f"\n🚀 Usage:")
    print(f"   python run.py                    # Show this help")
    print(f"   python run.py <server-name>      # Run specific server")
    
    print(f"\n📖 Examples:")
    for server_id in SERVERS.keys():
        print(f"   python run.py {server_id}")

def run_server(server_id: str):
    """Run the specified MCP server."""
    if server_id not in SERVERS:
        print(f"❌ Unknown server: {server_id}")
        print(f"Available servers: {', '.join(SERVERS.keys())}")
        return False
    
    server_config = SERVERS[server_id]
    server_path = Path(__file__).parent / server_config["path"]
    run_script = server_path / server_config["script"]
    
    if not run_script.exists():
        print(f"❌ Run script not found: {run_script}")
        return False
    
    print(f"🚀 Starting {server_config['name']}...")
    print(f"📁 Server path: {server_path}")
    print("-" * 50)
    
    try:
        # Change to server directory and run the script
        os.chdir(server_path)
        subprocess.run([sys.executable, str(run_script)], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed with exit code: {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
        return True
    except Exception as e:
        print(f"❌ Error running server: {e}")
        return False

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    server_id = sys.argv[1].lower()
    
    if server_id in ['-h', '--help', 'help']:
        show_help()
        return
    
    success = run_server(server_id)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
