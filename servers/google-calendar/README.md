# Google Calendar MCP Server

A FastMCP server that provides Google Calendar integration capabilities through webhook-based operations.

## 🚀 Features

- **Calendar Availability Checking**: Query calendar availability for specified date ranges
- **Appointment Booking**: Schedule meetings with detailed attendee information
- **Webhook Integration**: Seamless integration with external calendar systems
- **Structured Logging**: Built-in logging for monitoring and debugging

## 🛠️ Installation

### Prerequisites

- Python 3.10 or higher
- Access to the webhook endpoint for calendar operations

### Setup

1. **Install dependencies** (from project root):
   ```bash
   uv sync
   ```

2. **Set environment variables**:
   ```bash
   export GOOGLE_CALENDAR_WEBHOOK_URL="your-webhook-url"
   ```

## 🏃 Usage

### Running the Server

```bash
# Easiest method - from server directory
cd servers/google-calendar
python run.py

# From project root
python run.py google-calendar

# Using make (from project root)
make run-google-calendar

# Alternative methods
# Using uv
uv run --package google-calendar-server fastmcp run servers/google-calendar/src/google_calendar/main.py

# Using python module
cd servers/google-calendar/src
python -m google_calendar.main
```

### Available Tools

#### 1. `check_availability`

Check calendar availability for a given time range.

**Parameters:**
- `start_date` (str): Start date/time in ISO 8601 format with timezone
- `end_date` (str): End date/time in ISO 8601 format with timezone  
- `conversation_id` (str): Dynamic conversation identifier
- `callSid` (str): Dynamic call identifier
- `proposed_time` (str, optional): Specific proposed time in ISO 8601 format

**Example:**
```python
result = check_availability(
    start_date="2024-01-15T09:00:00+10:00",
    end_date="2024-01-22T17:00:00+10:00",
    conversation_id="conv_123",
    callSid="call_456"
)
```

#### 2. `book_appointment`

Schedule an appointment with attendee details.

**Parameters:**
- `attendee` (dict): Attendee information including:
  - `phone_number` (required): E.164 format phone number
  - `first_name` (required): Attendee's first name
  - `last_name` (required): Attendee's last name
  - `address` (required): Physical address
  - `email` (optional): RFC 5322 format email
- `time_utc` (str): Appointment time in ISO 8601 format
- `conversation_id` (str): Dynamic conversation identifier
- `callSid` (str): Dynamic call identifier
- `description` (str, optional): Appointment description

**Example:**
```python
attendee = {
    "phone_number": "+61403722371",
    "first_name": "John",
    "last_name": "Doe",
    "address": "123 Main St, Sydney",
    "email": "john.doe@example.com"
}

result = book_appointment(
    attendee=attendee,
    time_utc="2024-01-15T14:00:00+10:00",
    conversation_id="conv_123",
    callSid="call_456",
    description="Initial consultation"
)
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CALENDAR_WEBHOOK_URL` | Webhook URL for calendar operations | `https://vbe.alchemis.ai/webhook/c254fc1d-ff3b-40b8-b77e-da491bc55adb` |

### Configuration File

The server configuration is managed in `src/google_calendar/config.py`:

```python
import os

# Default Webhook URL if not specified in environment
DEFAULT_WEBHOOK_URL = "https://vbe.alchemis.ai/webhook/c254fc1d-ff3b-40b8-b77e-da491bc55adb"

# Environment Variables
WEBHOOK_URL = os.environ.get("GOOGLE_CALENDAR_WEBHOOK_URL", DEFAULT_WEBHOOK_URL)

# Constants
WEBHOOK_TIMEOUT_SECONDS = 20.0
```

## 🐳 Docker Support

Build and run the server in a container:

```bash
# Build the image
docker build -t google-calendar-server .

# Run the container
docker run -p 8000:8000 -e GOOGLE_CALENDAR_WEBHOOK_URL="your-url" google-calendar-server
```

## 🔧 Development

### Project Structure

```
google-calendar/
├── src/
│   └── google_calendar/
│       ├── __init__.py
│       ├── main.py          # FastMCP server implementation
│       └── config.py        # Configuration management
├── pyproject.toml           # Package configuration
├── README.md               # This file
└── Dockerfile             # Container configuration
```

### Adding Features

1. Extend the FastMCP server in `main.py`
2. Add new tools using the `@mcp.tool()` decorator
3. Update configuration in `config.py` as needed
4. Add tests for new functionality

### Testing

```bash
# Run tests (from project root)
uv run pytest servers/google-calendar/

# Run with coverage
uv run pytest --cov=google_calendar servers/google-calendar/
```

## 📝 API Reference

### Webhook Integration

The server communicates with external calendar systems through HTTP webhooks:

- **GET requests**: Used for availability checking
- **POST requests**: Used for appointment booking
- **Timeout**: 20 seconds default
- **Error handling**: Comprehensive error responses with logging

### Response Format

All tools return string responses that include:
- Success confirmations with relevant details
- Error messages with specific failure reasons
- Structured logging for debugging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

Part of the Chime Labs MCP Servers monorepo.
