# Build from the root of the monorepo:
# docker build -f servers/service-m8/Dockerfile -t mcp-service-m8 .

FROM python:3.10-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy the workspace definition and lock file
COPY pyproject.toml uv.lock* ./

# Copy specific server and shared code
COPY shared ./shared
COPY servers/service-m8 ./servers/service-m8

# Install dependencies for the specific server
# This relies on the root pyproject.toml defining the workspace
RUN uv sync --frozen --package service-m8-server

# Add the virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run the server
CMD ["uv", "run", "--package", "service-m8-server", "service-m8-server"]
