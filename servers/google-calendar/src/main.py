from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from shared_utils import setup_logger
import asyncio

# Initialize logger
logger = setup_logger("google-calendar-server")

# Create an MCP server
mcp = FastMCP("Google Calendar")

import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
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

async def _generate_available_slots(
    start_date: str,
    end_date: str,
    busy_periods: List[Dict[str, str]],
    timezone: str,
    booking_settings: Dict[str, Any]
) -> Dict[str, List[Dict[str, str]]]:
    """
    Generate available time slots based on business hours and busy periods.
    
    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format
        busy_periods: List of busy periods from Google Calendar
        timezone: User's timezone
        booking_settings: Business hours and slot configuration
    
    Returns:
        Dictionary of available slots organized by date
    """
    from datetime import datetime, timedelta
    import pytz
    
    # Parse dates
    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    # Get timezone object
    try:
        tz = pytz.timezone(timezone)
    except:
        tz = pytz.UTC
        logger.warning(f"Invalid timezone {timezone}, using UTC")
    
    # Convert to user timezone
    start_local = start_dt.astimezone(tz)
    end_local = end_dt.astimezone(tz)
    
    # Get business hours (default to 9-17 if not configured)
    business_hours = booking_settings.get('businessBookingHours', {
        'monday': {'enabled': True, 'startHour': 9, 'endHour': 17},
        'tuesday': {'enabled': True, 'startHour': 9, 'endHour': 17},
        'wednesday': {'enabled': True, 'startHour': 9, 'endHour': 17},
        'thursday': {'enabled': True, 'startHour': 9, 'endHour': 17},
        'friday': {'enabled': True, 'startHour': 9, 'endHour': 17},
        'saturday': {'enabled': False, 'startHour': 9, 'endHour': 17},
        'sunday': {'enabled': False, 'startHour': 9, 'endHour': 17}
    })
    
    slot_length = booking_settings.get('slotLengthMinutes', 60)
    buffer_minutes = booking_settings.get('bufferMinutes', 0)
    
    # Parse busy periods
    busy_times = []
    for busy in busy_periods:
        busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
        busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
        busy_times.append((busy_start, busy_end))
    
    # Generate slots
    slots = {}
    current_date = start_local.date()
    end_date_local = end_local.date()
    
    while current_date <= end_date_local:
        day_name = current_date.strftime('%A').lower()
        day_config = business_hours.get(day_name, {'enabled': False})
        
        if not day_config.get('enabled', False):
            current_date += timedelta(days=1)
            continue
        
        # Create slots for this day
        day_slots = []
        start_hour = day_config.get('startHour', 9)
        end_hour = day_config.get('endHour', 17)
        
        # Start from business hours
        slot_start = tz.localize(datetime.combine(current_date, datetime.min.time().replace(hour=start_hour)))
        day_end = tz.localize(datetime.combine(current_date, datetime.min.time().replace(hour=end_hour)))
        
        while slot_start + timedelta(minutes=slot_length) <= day_end:
            slot_end = slot_start + timedelta(minutes=slot_length)
            
            # Check if slot conflicts with busy periods
            is_busy = False
            for busy_start, busy_end in busy_times:
                if (slot_start < busy_end and slot_end > busy_start):
                    is_busy = True
                    break
            
            # Check if slot is in the future (with buffer)
            now = datetime.now(tz)
            min_advance = booking_settings.get('minimumAdvanceMinutes', 120)
            earliest_slot = now + timedelta(minutes=min_advance)
            
            # For availability checking, we should show all slots within the requested range
            # The minimum advance check should be applied at booking time, not availability checking
            if not is_busy and slot_start >= start_local and slot_end <= end_local:
                day_slots.append({
                    'time': slot_start.isoformat(),
                    'attendees': 1
                })
            
            slot_start += timedelta(minutes=slot_length)
        
        if day_slots:
            slots[current_date.strftime('%Y-%m-%d')] = day_slots
        
        current_date += timedelta(days=1)
    
    return slots


async def _check_availability_logic(
    call_sid: str,
    start_date: str,
    end_date: str,
    proposed_time: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check calendar availability logic matching n8n workflow.
    
    Steps:
    1. Fetch calendar settings (user settings, timezone, etc.)
    2. Query Cal.com API for available slots
    3. If proposed_time provided, check if it matches any available slot
    
    Args:
        call_sid: Twilio call SID
        start_date: Start date for availability check (ISO format)
        end_date: End date for availability check (ISO format)
        proposed_time: Optional specific time to check (ISO format)
        conversation_id: Optional conversation ID for tracking
    
    Returns:
        Dictionary with slots and match information
    """
    
    logger.info(f"Starting availability check for call_sid: {call_sid}, conversation_id: {conversation_id}, start: {start_date}, end: {end_date}")
    
    try:
        # Step 1: Fetch calendar settings using the same query as n8n flow
        logger.info(f"Step 1: Fetching calendar settings for call_sid: {call_sid}")
        context = await get_booking_context_by_call_sid(call_sid)
        
        if not context:
            logger.error(f"No booking context found for call_sid: {call_sid}")
            return {"error": "Unable to fetch calendar settings"}
        
        # Extract data from context
        user_settings = context.get('user_settings', {})
        user_profile = context.get('user_profile', {})
        
        # Get Google Calendar integration settings
        integration_settings = user_settings.get('integration_settings', {})
        calendar_settings = integration_settings.get('calendar', {})
        google_cal_integration = calendar_settings.get('google_calendar', {})
        
        if not google_cal_integration:
            logger.error("No Google Calendar integration found in user settings")
            logger.debug(f"Available integration settings: {integration_settings.keys()}")
            return {"error": "No Google Calendar integration configured"}
        
        # Extract Google Calendar credentials and settings
        access_token = google_cal_integration.get('access_token')
        calendars = google_cal_integration.get('calendars', [])
        selected_calendar = google_cal_integration.get('selected_calendar')
        timezone = user_profile.get('timezone', 'UTC')
        
        logger.debug(f"Google Calendar integration found - token present: {bool(access_token)}")
        logger.debug(f"Selected calendar: {selected_calendar}, Available calendars: {len(calendars)}")
        logger.debug(f"Using timezone: {timezone}")
        
        if not access_token:
            logger.error("Missing Google Calendar access token")
            return {"error": "Google Calendar integration not properly configured - missing access token"}
        
        if not selected_calendar:
            # Fallback: use primary calendar if no specific calendar is selected
            logger.warning("No calendar selected, attempting to use primary calendar")
            selected_calendar = 'primary'
            logger.info(f"Using fallback primary calendar for availability checking")
        
        # Step 2: Validate and refresh Google Calendar token if needed
        logger.info(f"Step 2: Validating and refreshing Google Calendar token")
        user_id = user_settings.get('user_id')
        if not user_id:
            logger.error("No user_id found in user settings")
            return {"error": "User ID not found"}
        
        token_data = await validate_and_refresh_gcal_token(user_id, user_settings)
        if not token_data:
            logger.error(f"Failed to validate/refresh Google Calendar token for user: {user_id}")
            return {"error": "Unable to validate Google Calendar credentials"}
        
        # Use the validated/refreshed token
        validated_access_token = token_data.get('access_token', access_token)
        logger.info(f"Using validated access token for Google Calendar API")
        
        # Step 3: Query Google Calendar FreeBusy API for availability
        logger.info(f"Step 3: Querying Google Calendar FreeBusy API for availability")
        
        async with httpx.AsyncClient() as client:
            headers = {
                'Authorization': f'Bearer {validated_access_token}',
                'Content-Type': 'application/json'
            }
            
            # Google Calendar FreeBusy API request
            freebusy_request = {
                "timeMin": start_date,
                "timeMax": end_date,
                "timeZone": timezone,
                "items": [{"id": selected_calendar}]
            }
            
            response = await client.post(
                'https://www.googleapis.com/calendar/v3/freeBusy',
                headers=headers,
                json=freebusy_request
            )
            
            if response.status_code != 200:
                logger.error(f"Google Calendar API error: {response.status_code} - {response.text}")
                return {"error": f"Google Calendar API error: {response.status_code}"}
            
            freebusy_data = response.json()
            busy_periods = freebusy_data.get('calendars', {}).get(selected_calendar, {}).get('busy', [])
            
            logger.info(f"Retrieved {len(busy_periods)} busy periods from Google Calendar")
            
            # Generate available slots based on business hours and busy periods
            slots = await _generate_available_slots(
                start_date, end_date, busy_periods, timezone, context.get('booking_settings', {})
            )
        
        # Step 3: Check proposed time if provided
        match_found = False
        matching_slot = None
        
        if proposed_time:
            logger.info(f"Step 3: Checking proposed time: {proposed_time}")
            
            # Parse proposed time
            from datetime import datetime
            try:
                proposed_dt = datetime.fromisoformat(proposed_time.replace('Z', '+00:00'))
                proposed_timestamp = int(proposed_dt.timestamp() * 1000)  # Convert to milliseconds
                
                # Search through all slots
                for date_key, date_slots in slots.items():
                    for slot in date_slots:
                        slot_time = slot.get('time')
                        if slot_time:
                            slot_dt = datetime.fromisoformat(slot_time.replace('Z', '+00:00'))
                            slot_timestamp = int(slot_dt.timestamp() * 1000)
                            
                            if slot_timestamp == proposed_timestamp:
                                match_found = True
                                matching_slot = slot
                                break
                    if match_found:
                        break
                        
                logger.info(f"Proposed time match: {match_found}")
                        
            except Exception as e:
                logger.error(f"Error parsing proposed time: {e}")
        
        return {
            "slots": slots,
            "matchFound": match_found,
            "matchingSlot": matching_slot,
            "timezone": timezone,
            "totalSlots": sum(len(date_slots) for date_slots in slots.values())
        }
        
    except Exception as e:
        logger.error(f"Error in availability check logic: {str(e)}", exc_info=True)
        return {"error": f"Availability check failed: {str(e)}"}


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
def check_availability(
    call_sid: str,
    start_date: str,
    end_date: str,
    proposed_time: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> Any:
    """
    Check calendar availability for a given date range.
    
    This tool queries the user's calendar integration (Cal.com) to find available appointment slots
    within the specified date range. It can also check if a specific proposed time is available.
    
    Args:
        call_sid: Twilio call SID for identifying the user's calendar settings
        start_date: Start date for availability check in ISO 8601 format (e.g., "2025-01-20T00:00:00Z")
        end_date: End date for availability check in ISO 8601 format (e.g., "2025-01-27T23:59:59Z")
        proposed_time: Optional specific time to check availability for in ISO 8601 format
        conversation_id: Optional conversation ID for tracking purposes
    
    Returns:
        Dictionary containing:
        - slots: Available time slots organized by date
        - matchFound: Boolean indicating if proposed_time matches an available slot (if provided)
        - matchingSlot: The matching slot details (if found)
        - timezone: User's timezone
        - totalSlots: Total number of available slots
        - error: Error message if something went wrong
    """
    
    try:
        # Check if there's already a running event loop
        loop = asyncio.get_running_loop()
        # If we're in an async context, we need to handle this differently
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _check_availability_logic(call_sid, start_date, end_date, proposed_time, conversation_id))
            return future.result()
    except RuntimeError:
        # No running event loop, safe to use asyncio.run()
        return asyncio.run(_check_availability_logic(call_sid, start_date, end_date, proposed_time, conversation_id))


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
