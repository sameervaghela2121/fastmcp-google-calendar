from fastmcp import FastMCP
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
from database import initialize_database, cleanup_database, get_booking_context_by_callsid, validate_and_refresh_gcal_token, create_google_calendar_event

# ... (setup_logger and mcp initialization remain)

def _check_availability_logic(
    start_date: str,
    end_date: str,
    conversation_id: str,
    callSid: str,
    proposed_time: Optional[str] = None
) -> str:
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "conversation_id": conversation_id,
        "callSid": callSid
    }
    
    if proposed_time:
        params["proposed_time"] = proposed_time
        
    try:
        logger.info(f"Checking availability from {start_date} to {end_date}")
        response = httpx.get(
            config.WEBHOOK_URL, 
            params=params, 
            timeout=config.WEBHOOK_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.text
        
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return f"Failed to check availability: {error_msg}"
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        logger.error(error_msg)
        return f"Failed to check availability: {error_msg}"

@mcp.tool()
def check_availability(
    start_date: str,
    end_date: str,
    conversation_id: str,
    callSid: str,
    proposed_time: Optional[str] = None
) -> str:
    """
    Check availability for a given time range.
    
    Args:
        start_date: Resolved start date/time in ISO 8601 extended format with timezone offset.
        end_date: Resolved end date/time in ISO 8601 extended format with timezone offset. 
                  Typically start_date + 7 days (or 6 weeks if specific date provided).
        conversation_id: Dynamic Variable system__conversation_id
        callSid: Dynamic Variable callSid
        proposed_time: Specific time proposed by user in ISO 8601 extended format (optional).
    """
    return _check_availability_logic(start_date, end_date, conversation_id, callSid, proposed_time)

def _book_appointment_logic(
    attendee: Dict[str, Any],
    time_utc: str,
    conversation_id: str,
    callSid: str,
    description: Optional[str] = None
) -> str:
    # First, fetch booking context data using the callSid
    try:
        booking_context = asyncio.run(get_booking_context_by_callsid(callSid))
        
        if booking_context:
            logger.info(f"Retrieved booking context for callSid: {callSid}")
            
            # Extract relevant information from booking context
            api_key = booking_context.get('apiKey')
            user_settings = booking_context.get('user_settings', {})
            agent_info = booking_context.get('agent', {})
            campaign_info = booking_context.get('campaign', {})
            contact_info = booking_context.get('contact', {})
            user_profile = booking_context.get('user_profile', {})
            booking_settings = booking_context.get('booking_settings', {})
            
            # Log the retrieved context for debugging
            logger.debug(f"Booking context - API Key: {'***' if api_key else 'None'}")
            logger.debug(f"User settings: {user_settings.get('user_id') if user_settings else 'None'}")
            logger.debug(f"Agent: {agent_info.get('name') if agent_info else 'None'}")
            logger.debug(f"Campaign: {campaign_info.get('name') if campaign_info else 'None'}")
            
            # Validate and refresh Google Calendar token if needed
            gcal_token_data = None
            gcal_event_result = None
            if user_settings:
                user_id = user_settings.get('user_id')
                if user_id:
                    try:
                        gcal_token_data = asyncio.run(validate_and_refresh_gcal_token(user_id, user_settings))
                        if gcal_token_data:
                            logger.info(f"Google Calendar token validated for user {user_id}")
                            
                            # Book the event directly in Google Calendar
                            try:
                                gcal_event_result = asyncio.run(create_google_calendar_event(
                                    token_data=gcal_token_data,
                                    attendee=attendee,
                                    time_utc=time_utc,
                                    description=description,
                                    duration_minutes=60  # Default 1 hour appointment
                                ))
                                
                                if gcal_event_result:
                                    logger.info(f"Successfully created Google Calendar event: {gcal_event_result.get('event_id')}")
                                else:
                                    logger.warning(f"Failed to create Google Calendar event for user {user_id}")
                                    
                            except Exception as booking_error:
                                logger.error(f"Error creating Google Calendar event: {str(booking_error)}")
                        else:
                            logger.warning(f"Google Calendar token validation failed for user {user_id}")
                    except Exception as token_error:
                        logger.error(f"Error validating Google Calendar token: {str(token_error)}")
            
            # Enhance the payload with context data and token information
            enhanced_payload = {
                "Description": description or f"Appointment for {attendee.get('first_name')} {attendee.get('last_name')}",
                "attendee": attendee,
                "time_utc": time_utc,
                "booking_context": {
                    "api_key": api_key,
                    "user_settings": user_settings,
                    "agent": agent_info,
                    "campaign": campaign_info,
                    "contact": contact_info,
                    "user_profile": user_profile,
                    "booking_settings": booking_settings,
                    "gcal_token_data": gcal_token_data,
                    "gcal_event_result": gcal_event_result
                }
            }
            
            payload = enhanced_payload
        else:
            logger.warning(f"No booking context found for callSid: {callSid}, proceeding with basic payload")
            payload = {
                "Description": description or f"Appointment for {attendee.get('first_name')} {attendee.get('last_name')}",
                "attendee": attendee,
                "time_utc": time_utc
            }
            
    except Exception as context_error:
        logger.error(f"Error fetching booking context: {str(context_error)}, proceeding with basic payload")
        payload = {
            "Description": description or f"Appointment for {attendee.get('first_name')} {attendee.get('last_name')}",
            "attendee": attendee,
            "time_utc": time_utc
        }
    
    params = {
        "conversation_id": conversation_id,
        "callSid": callSid
    }

    try:
        logger.info(f"Booking appointment for {attendee.get('phone_number')} at {time_utc}")
        response = httpx.post(
            config.WEBHOOK_URL, 
            json=payload, 
            params=params, 
            timeout=config.WEBHOOK_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        
        return f"Successfully booked appointment. Response: {response.text}"
        
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return f"Failed to book appointment: {error_msg}"
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        logger.error(error_msg)
        return f"Failed to book appointment: {error_msg}"

@mcp.tool()
def book_appointment(
    attendee: Dict[str, Any],
    time_utc: str,
    conversation_id: str,
    callSid: str,
    description: Optional[str] = None
) -> str:
    """
    Use this tool to schedule a meeting or appointment for the user.
    
    Only book a time that is available in the list returned by the `check_availability` tool.
    Provide the desired date and time in ISO 8601 extended format with the appropriate timezone offset (e.g., 2025-07-05T11:00:00+10:00).
    Interpret all user-specified dates and times—including relative expressions like "tomorrow at 11" or "next Monday"—using the provided reference time.
    Return the resolved date and time as the `time_utc` parameter.
    If booking fails, suggest an alternative time without referencing the error.
    
    Args:
        attendee: Dictionary containing attendee details:
            - phone_number (required): E.164 format (e.g., +61403722371)
            - first_name (required)
            - last_name (required)
            - address (required): Physical address. Format: [Unit Number] [Street Number] [Street Name] [Street Type], [Suburb]
            - email (optional): RFC 5322 format
        time_utc: Resolved date and time in the user's timezone, ISO 8601 extended format.
        conversation_id: Dynamic Variable system__conversation_id
        callSid: Dynamic Variable callSid
        description: description of the appointment
    """
    return _book_appointment_logic(attendee, time_utc, conversation_id, callSid, description)


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
        mcp.run()
        # mcp.run(transport="http", port=8000)
    finally:
        # Clean up on shutdown
        asyncio.run(shutdown())

if __name__ == "__main__":
    main()
