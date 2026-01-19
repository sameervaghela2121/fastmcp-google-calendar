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
from shared_utils import (
    get_shared_config,
    initialize_database, 
    cleanup_database, 
    get_booking_context_by_call_sid,
    store_event_booking,
    update_call_history_booking,
    validate_and_refresh_gcal_token,
    create_google_calendar_event
)

async def _book_appointment_logic(
    call_sid: str,
    time_utc: str,
    attendee: Dict[str, Any],
) -> str:
    """
    Complete booking logic matching n8n workflow.
    
    Steps:
    1. Fetch booking context (user settings, campaign, contact, etc.)
    2. Validate/refresh Google Calendar token
    3. Create Google Calendar event
    4. Store booking in event_bookings table
    5. Update call_history with booking outcome
    """
    
    logger.info(f"Starting booking for call_sid: {call_sid}, time: {time_utc}")
    
    if not call_sid:
        logger.warning("No call_sid provided")
        return "Error: call_sid is required"
    
    try:
        # Step 1: Fetch booking context
        logger.info(f"Step 1: Fetching booking context for call_sid: {call_sid}")
        context = await get_booking_context_by_call_sid(call_sid)
        
        if not context:
            logger.error(f"No booking context found for call_sid: {call_sid}")
            return "Error: Unable to fetch booking context"
        
        # Extract data from context
        user_settings = context.get('user_settings', {})
        user_profile = context.get('user_profile', {})
        call_history = context.get('call_history', {})
        contact = context.get('contact', {})
        booking_settings = context.get('booking_settings', {})
        
        user_id = user_settings.get('user_id')
        if not user_id:
            logger.error("No user_id found in booking context")
            return "Error: User ID not found"
        
        # Check if primary calendar integration is Google Calendar
        primary_integration = user_settings.get('primary_calendar_integration')
        if primary_integration != 'google_calendar':
            logger.warning(f"Primary calendar integration is not Google Calendar: {primary_integration}")
            return f"Error: Primary calendar integration is {primary_integration}, not google_calendar"
        
        # Step 2: Validate and refresh token if needed
        logger.info(f"Step 2: Validating Google Calendar token for user: {user_id}")
        token_data = await validate_and_refresh_gcal_token(user_id, user_settings)
        
        if not token_data:
            logger.error(f"Failed to validate/refresh Google Calendar token for user: {user_id}")
            return "Error: Unable to validate Google Calendar credentials"
        
        # Step 3: Create Google Calendar event
        logger.info(f"Step 3: Creating Google Calendar event")
        
        # Get slot length from booking settings (default 60 minutes)
        duration_minutes = booking_settings.get('slotLengthMinutes', 60) if booking_settings else 60
        
        # Get phone number from call history
        phone_number = call_history.get('inbound_from_phone_number')
        
        event_data = await create_google_calendar_event(
            token_data=token_data,
            attendee=attendee,
            time_utc=time_utc,
            phone_number=phone_number,
            duration_minutes=duration_minutes
        )
        
        if not event_data:
            logger.error("Failed to create Google Calendar event")
            return "Error: Failed to create calendar event"
        
        logger.info(f"Successfully created Google Calendar event: {event_data.get('id')}")
        
        # Step 4: Store booking in event_bookings table
        logger.info(f"Step 4: Storing booking in event_bookings table")
        contact_id = contact.get('id') if contact else None
        
        booking_id = await store_event_booking(
            user_id=user_id,
            contact_id=contact_id,
            event_data=event_data,
            source="google_calendar"
        )
        
        if not booking_id:
            logger.error("Failed to store event booking")
            return "Error: Failed to store booking record"
        
        logger.info(f"Successfully stored event booking: {booking_id}")
        
        # Step 5: Update call_history with booking outcome
        logger.info(f"Step 5: Updating call_history with booking outcome")
        update_success = await update_call_history_booking(
            call_sid=call_sid,
            event_booking_id=booking_id
        )
        
        if not update_success:
            logger.warning(f"Failed to update call_history, but booking was created")
        
        # Return success message
        event_link = event_data.get('htmlLink', '')
        return f"Successfully booked appointment for {attendee.get('first_name', '')} {attendee.get('last_name', '')} at {time_utc}. Event ID: {event_data.get('id')}"

    except Exception as e:
        logger.error(f"Error in booking logic: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"



@mcp.tool()
def book_appointment(
    call_sid: str,
    time_utc: str,
    attendee_first_name: str,
    attendee_last_name: str,
    attendee_email: Optional[str] = None,
    attendee_phone_number: Optional[str] = None,
    attendee_address: Optional[str] = None,
) -> Any:
    """
    Use this tool to schedule a meeting or appointment for the user in Google Calendar.
    
    Only book a time that is available in the list returned by the `check_availability` tool.
    Provide the desired date and time in ISO 8601 extended format with the appropriate timezone offset (e.g., 2025-07-05T11:00:00+10:00).
    Interpret all user-specified dates and times—including relative expressions like "tomorrow at 11" or "next Monday"—using the provided reference time.
    If booking fails, suggest an alternative time without referencing the error.
    
    Args:
        call_sid: Twilio call SID (automatically extracted from HTTP headers)
        time_utc: Appointment start time in ISO 8601 format (e.g., "2025-07-05T11:00:00+10:00")
        attendee_first_name: Attendee's first name
        attendee_last_name: Attendee's last name
        attendee_email: Attendee's email address (optional)
        attendee_phone_number: Attendee's phone number (optional)
        attendee_address: Attendee's address/location (optional)
    
    Returns:
        Success message with booking details or error message
    
    Note: call_sid is automatically extracted from HTTP headers (x-twilio-callsid, callsid, or Call-SID).
    """
    # Build attendee dictionary
    attendee = {
        'first_name': attendee_first_name,
        'last_name': attendee_last_name,
        'email': attendee_email,
        'phone_number': attendee_phone_number,
        'address': attendee_address
    }
    
    try:
        # Check if there's already a running event loop
        loop = asyncio.get_running_loop()
        # If we're in an async context, we need to handle this differently
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _book_appointment_logic(call_sid, time_utc, attendee))
            return future.result()
    except RuntimeError:
        # No running event loop, safe to use asyncio.run()
        return asyncio.run(_book_appointment_logic(call_sid, time_utc, attendee))


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
