from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from shared_utils import setup_logger
import asyncio

# Initialize logger
logger = setup_logger("google-calendar-server")

# Create an MCP server
mcp = FastMCP("Google Calendar")

import httpx
from datetime import datetime
from typing import Optional, Dict, Any
import config
from database import initialize_database, cleanup_database, get_booking_context_by_call_sid, validate_and_refresh_gcal_token, create_google_calendar_event

async def _book_appointment_logic(
    call_sid: str,
) -> str:
    
    print(f"DEBUG: _book_appointment_logic called with call_sid: {call_sid}")
    
    if not call_sid:
        logger.warning("No call_sid found")
        call_sid = "unknown"
    
    # Step 1: Fetch User Settings
    try:
        logger.info(f"_book_appointment_logic: Booking {call_sid}")
        print(f"DEBUG: About to call get_booking_context_by_call_sid")
        user_settings = await get_booking_context_by_call_sid(call_sid)
        print(f"DEBUG: get_booking_context_by_call_sid returned: {user_settings}")

    except Exception as context_error:
        print(f"DEBUG: Exception in _book_appointment_logic: {str(context_error)}")
        logger.error(f"Error fetching booking context: {str(context_error)}, proceeding with basic payload")
    
    print(f"DEBUG: _book_appointment_logic completed")
    return f"Booking logic completed for call_sid: {call_sid}"



@mcp.tool()
def book_appointment(
    call_sid: str,
) -> Any:
    """
    Use this tool to schedule a meeting or appointment for the user.
    
    Only book a time that is available in the list returned by the `check_availability` tool.
    Provide the desired date and time in ISO 8601 extended format with the appropriate timezone offset (e.g., 2025-07-05T11:00:00+10:00).
    Interpret all user-specified dates and times—including relative expressions like "tomorrow at 11" or "next Monday"—using the provided reference time.
    Return the resolved date and time as the `time_utc` parameter.
    If booking fails, suggest an alternative time without referencing the error.
    
    Args:
        call_sid: caller user id
    
    Note: call_sid is automatically extracted from HTTP headers (x-twilio-callsid, callsid, or Call-SID).
    """
    try:
        # Check if there's already a running event loop
        loop = asyncio.get_running_loop()
        # If we're in an async context, we need to handle this differently
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _book_appointment_logic(call_sid))
            return future.result()
    except RuntimeError:
        # No running event loop, safe to use asyncio.run()
        return asyncio.run(_book_appointment_logic(call_sid))


@mcp.tool()
def say_hello():
    return "Hello from google calendar mcp!"

async def startup():
    """Initialize database connection on server startup."""
    logger.info("Starting Google Calendar MCP server...")
    success = await initialize_database()
    if success:
        logger.info("Database connection established successfully")
    else:
        logger.warning("Database connection failed - server will continue without database")

async def shutdown():
    """Clean up database connection on server shutdown."""
    logger.info("Shutting down Google Calendar MCP server...")
    await cleanup_database()

def main():
    # Initialize database on startup
    asyncio.run(startup())
    
    try:
        # mcp.run()
        mcp.run(transport="http", port=8000)
    finally:
        # Clean up on shutdown
        asyncio.run(shutdown())

if __name__ == "__main__":
    main()
