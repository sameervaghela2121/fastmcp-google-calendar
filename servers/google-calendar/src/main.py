from fastmcp import FastMCP
from shared_utils import setup_logger

# Initialize logger
logger = setup_logger("google-calendar-server")

# Create an MCP server
mcp = FastMCP("Google Calendar")

import httpx
from datetime import datetime
from typing import Optional, Dict, Any
import config

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

def main():
    mcp.run()
    # mcp.run(transport="http", port=8000)

if __name__ == "__main__":
    main()
