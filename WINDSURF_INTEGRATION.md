# Windsurf MCP Integration Guide

This guide shows you how to run your MCP servers and integrate them with Windsurf IDE.

## 🚀 Running MCP Servers

### Method 1: Direct Python Execution

```bash
# From project root
cd /home/sam/Downloads/chimelabs_mcp_servers

# Show available servers
python3 run.py

# Run Google Calendar server
python3 run.py google-calendar

# Or run directly from server directory
cd servers/google-calendar
python3 run.py
```

### Method 2: Using Make Commands

```bash
cd /home/sam/Downloads/chimelabs_mcp_servers

# Run Google Calendar server
make run-google-calendar

# Run any server
make run-server SERVER=google-calendar
```

## 🔧 Windsurf Integration

### Step 1: Locate Windsurf MCP Configuration

Windsurf stores MCP server configurations in your user settings. The location depends on your system:

**Linux:**
```
~/.config/windsurf/mcp_servers.json
```

**macOS:**
```
~/Library/Application Support/windsurf/mcp_servers.json
```

**Windows:**
```
%APPDATA%\windsurf\mcp_servers.json
```

### Step 2: Add MCP Server Configuration

Add this configuration to your Windsurf `mcp_servers.json` file:

```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "python3",
      "args": [
        "/home/sam/Downloads/chimelabs_mcp_servers/servers/google-calendar/run.py"
      ],
      "env": {
        "GOOGLE_CALENDAR_WEBHOOK_URL": "https://vbe.alchemis.ai/webhook/c254fc1d-ff3b-40b8-b77e-da491bc55adb"
      }
    }
  }
}
```

**Important:** Update the path in `args` to match your actual project location.

### Step 3: Alternative Configuration Methods

#### Option A: Using Central Runner
```json
{
  "mcpServers": {
    "chime-labs-servers": {
      "command": "python3",
      "args": [
        "/home/sam/Downloads/chimelabs_mcp_servers/run.py",
        "google-calendar"
      ],
      "env": {
        "GOOGLE_CALENDAR_WEBHOOK_URL": "https://vbe.alchemis.ai/webhook/c254fc1d-ff3b-40b8-b77e-da491bc55adb"
      }
    }
  }
}
```

#### Option B: Using UV (if preferred)
```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "uv",
      "args": [
        "run",
        "--package",
        "google-calendar-server",
        "fastmcp",
        "run",
        "/home/sam/Downloads/chimelabs_mcp_servers/servers/google-calendar/src/google_calendar/main.py"
      ],
      "cwd": "/home/sam/Downloads/chimelabs_mcp_servers",
      "env": {
        "GOOGLE_CALENDAR_WEBHOOK_URL": "https://vbe.alchemis.ai/webhook/c254fc1d-ff3b-40b8-b77e-da491bc55adb"
      }
    }
  }
}
```

### Step 4: Restart Windsurf

After adding the configuration:
1. Save the `mcp_servers.json` file
2. Restart Windsurf IDE
3. The MCP server should be available in your Windsurf session

## 🔍 Verification

### Test MCP Server Connection

1. **In Windsurf Chat:** Try using the MCP tools:
   ```
   Can you check calendar availability for next week?
   ```

2. **Check Server Logs:** The server will output logs when running:
   ```bash
   🚀 Starting Google Calendar MCP Server...
   📁 Working directory: /home/sam/Downloads/chimelabs_mcp_servers/servers/google-calendar
   🔧 Webhook URL: https://vbe.alchemis.ai/webhook/c254fc1d-ff3b-40b8-b77e-da491bc55adb
   --------------------------------------------------
   ```

### Available MCP Tools

Once connected, you'll have access to these tools in Windsurf:

1. **`check_availability`**
   - Check calendar availability for date ranges
   - Parameters: start_date, end_date, conversation_id, callSid, proposed_time

2. **`book_appointment`**
   - Schedule appointments with attendee details
   - Parameters: attendee, time_utc, conversation_id, callSid, description

## 🛠️ Troubleshooting

### Common Issues

1. **Python not found:**
   - Use `python3` instead of `python` in the command
   - Ensure Python 3.10+ is installed

2. **Path issues:**
   - Use absolute paths in the configuration
   - Verify the file paths exist

3. **Dependencies missing:**
   ```bash
   cd /home/sam/Downloads/chimelabs_mcp_servers
   uv sync  # or pip install -r requirements.txt
   ```

4. **Environment variables:**
   - Set `GOOGLE_CALENDAR_WEBHOOK_URL` if using a custom webhook
   - Check the `.env.example` file for reference

### Debug Mode

Run the server manually to see detailed logs:

```bash
cd /home/sam/Downloads/chimelabs_mcp_servers/servers/google-calendar
python3 run.py
```

## 🔄 Adding More Servers

When you add new MCP servers to the project:

1. Create a new server directory under `servers/`
2. Add a `run.py` file in the server directory
3. Update the `SERVERS` dictionary in the root `run.py`
4. Add the new server to your Windsurf `mcp_servers.json`

## 📝 Environment Configuration

Create a `.env` file in your project root:

```bash
cp .env.example .env
# Edit .env with your actual values
```

The servers will automatically load environment variables from this file.

## 🔗 Useful Commands

```bash
# Show help
python3 run.py

# Test server directly
cd servers/google-calendar && python3 run.py

# Install dependencies
uv sync

# Run tests
make test

# Format code
make format
```
