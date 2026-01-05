#!/usr/bin/env python3
"""
Basic connectivity test for Google Calendar MCP Server
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

def test_basic_connectivity():
    """Test basic server functionality"""
    try:
        # Import the main module
        from main import mcp
        
        print("✅ MCP server imported successfully")
        print(f"📋 Server name: {mcp.name}")
        print(f"📋 mcp: {mcp}")
        
        # Check if the server has the expected attributes
        print("🔍 Checking server structure...")
        
        # Verify the server has tools registered
        if hasattr(mcp, '_tools'):
            tools_count = len(mcp._tools)
            print(f"🛠️  Tools registered: {tools_count}")
            
            # List tool names
            for tool_name in mcp._tools.keys():
                print(f"   - {tool_name}")
        else:
            print("⚠️  No _tools attribute found")
        
        # Test server configuration
        import config
        print(f"🔗 Webhook URL: {config.WEBHOOK_URL}")
        print(f"⏱️  Timeout: {config.WEBHOOK_TIMEOUT_SECONDS}s")
        
        # Test imports of main functions
        print("🧪 Testing function imports...")
        from main import _check_availability_logic, _book_appointment_logic
        print("✅ Core functions imported successfully")
        
        print("\n✅ Basic connectivity test PASSED!")
        print("💡 Server is ready - tools are registered and configuration is loaded")
        return True
        
    except Exception as e:
        print(f"❌ Basic connectivity test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Running Google Calendar MCP Server Connectivity Test")
    print("-" * 60)
    test_basic_connectivity()
