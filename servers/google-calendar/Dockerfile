# Build from the root of the monorepo:
# docker build -f servers/google-calendar/Dockerfile -t mcp-google-calendar .

FROM python:3.10-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy the workspace definition and lock file
COPY pyproject.toml uv.lock* ./

# Copy specific server and shared code
COPY shared ./shared
COPY servers/google-calendar ./servers/google-calendar

# Install dependencies for the specific server
# This relies on the root pyproject.toml defining the workspace
RUN uv sync --frozen --package google-calendar-server

# Add the virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run the server
CMD ["uv", "run", "--package", "google-calendar-server", "google-calendar-server"]
