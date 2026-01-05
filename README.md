# Chime Labs MCP Servers

A monorepo containing Model Context Protocol (MCP) servers developed by Chime Labs. MCP is a standard that enables AI systems to securely connect with external tools and data sources.

## 🏗️ Project Structure

```
chimelabs_mcp_servers/
├── shared/                 # Shared utilities and common code
│   ├── src/
│   │   └── shared_utils/   # Logger and utility functions
│   └── pyproject.toml      # Shared package configuration
├── servers/                # Individual MCP server implementations
│   └── google-calendar/    # Google Calendar integration server
│       ├── src/
│       │   └── google_calendar/
│       │       ├── main.py     # FastMCP server implementation
│       │       ├── config.py   # Configuration and environment variables
│       │       └── __init__.py
│       ├── pyproject.toml      # Server-specific dependencies
│       ├── README.md           # Server documentation
│       └── Dockerfile          # Container configuration
├── pyproject.toml          # Workspace configuration
└── requirements.txt        # Consolidated dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended) or `pip`

### Installation

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd chimelabs_mcp_servers
   ```

2. **Install dependencies using uv (recommended):**

   ```bash
   uv sync
   ```

   **Or using pip:**

   ```bash
   pip install -r requirements.txt
   ```

### Running Servers

You can run servers using the convenient `run.py` scripts:

```bash
# Run from project root - shows available servers
python run.py

# Run specific server from project root
python run.py google-calendar

# Or run directly from server directory
cd servers/google-calendar
python run.py

# Using make commands
make run-google-calendar
make run-server SERVER=google-calendar
```

#### Alternative Methods

```bash
# Using uv (if preferred)
uv run --package google-calendar-server fastmcp run servers/google-calendar/src/google_calendar/main.py

# Or using python module
cd servers/google-calendar/src
python -m google_calendar.main
```

## 📋 Available Servers

### Google Calendar Server

A FastMCP server that provides calendar integration capabilities including:

- **Check Availability**: Query calendar availability for specified date ranges
- **Book Appointments**: Schedule meetings with attendee details
- **Webhook Integration**: Connects to external calendar systems via webhooks

#### Environment Variables

| Variable                      | Description                         | Default                                                                |
| ----------------------------- | ----------------------------------- | ---------------------------------------------------------------------- |
| `GOOGLE_CALENDAR_WEBHOOK_URL` | Webhook URL for calendar operations | `https://vbe.alchemis.ai/webhook/c254fc1d-ff3b-40b8-b77e-da491bc55adb` |

#### Tools Available

1. **`check_availability`**

   - Check calendar availability for a date range
   - Parameters: start_date, end_date, conversation_id, callSid, proposed_time (optional)

2. **`book_appointment`**
   - Schedule appointments with attendee details
   - Parameters: attendee (dict), time_utc, conversation_id, callSid, description (optional)

## 🛠️ Development

### Workspace Management

This project uses `uv` workspace management with the following structure:

- **Root workspace**: Manages overall project dependencies
- **Shared package**: Common utilities used across servers
- **Server packages**: Individual MCP server implementations

### Adding New Servers

1. Create a new directory under `servers/`
2. Add `pyproject.toml` with appropriate dependencies
3. Include `shared_utils` as a dependency
4. Update the root workspace members in `pyproject.toml`

### Development Commands

```bash
# Sync all workspace dependencies
uv sync

# Run tests (if available)
uv run pytest

# Install in development mode
uv sync --dev

# Add dependencies to a specific package
cd servers/google-calendar
uv add <package-name>
```

### Docker Support

Each server includes a Dockerfile for containerized deployment:

```bash
# Build Google Calendar server
cd servers/google-calendar
docker build -t google-calendar-server .

# Run container
docker run -p 8000:8000 google-calendar-server
```

## 🔧 Configuration

### Shared Configuration

The shared utilities provide:

- **Logger setup**: Standardized logging across all servers
- **Common utilities**: Reusable functions and classes

### Server-Specific Configuration

Each server maintains its own configuration in `config.py`:

- Environment variable management
- Default values and constants
- Service-specific settings

## 📚 Dependencies

### Core Dependencies

- **FastMCP**: Framework for building MCP servers
- **httpx**: HTTP client for external API calls
- **pydantic**: Data validation and serialization

### Development Dependencies

- **pytest**: Testing framework
- **black**: Code formatting
- **mypy**: Type checking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For questions or issues:

- Create an issue in the repository
- Contact the Chime Labs team
- Check the documentation for each server

## 🔗 Related Links

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [uv Package Manager](https://github.com/astral-sh/uv)
