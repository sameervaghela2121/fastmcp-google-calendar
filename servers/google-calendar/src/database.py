"""
Database module for Google Calendar MCP server with Supabase integration.
Provides connection management and basic database operations.
"""

import os
import logging
from typing import Dict, Any, Optional
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from shared_utils import setup_logger

logger = setup_logger("google-calendar-database")


class SupabaseDatabase:
    """
    Supabase database connection and operations manager.
    """
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._connected = False
        
    def connect(self) -> bool:
        """
        Establish connection to Supabase database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Get Supabase credentials from environment
            supabase_url = SUPABASE_URL
            supabase_key = SUPABASE_ANON_KEY
            
            if not supabase_url or not supabase_key:
                logger.error("Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")
                return False
            
            # Create Supabase client
            client = create_client(supabase_url, supabase_key)
            self.client = client
            
            # Test connection by attempting a simple query
            self._test_connection()
            
            self._connected = True
            logger.info("Successfully connected to Supabase database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Supabase database: {str(e)}")
            self._connected = False
            return False
    
    def _test_connection(self):
        """
        Test the database connection by performing a simple query.
        """
        try:
            # Attempt to query a system table or perform a basic operation
            # This will raise an exception if connection fails
            result = self.client.table("call_history").select("count", count="exact").execute()
            logger.debug("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            raise
    
    def disconnect(self):
        """
        Close the database connection.
        """
        try:
            if self.client:
                # Supabase client doesn't require explicit disconnection
                # but we can clean up our references
                self.client = None
                self._connected = False
                logger.info("Disconnected from Supabase database")
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
    
    def is_connected(self) -> bool:
        """
        Check if database is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self._connected and self.client is not None
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Context manager for database operations.
        Ensures connection is available and handles cleanup.
        """
        if not self.is_connected():
            if not self.connect():
                raise Exception("Unable to establish database connection")
        
        try:
            yield self.client
        finally:
            # Supabase handles connection pooling automatically
            # No explicit cleanup needed for individual operations
            pass


# Global database instance
db = SupabaseDatabase()


async def initialize_database() -> bool:
    """
    Initialize the database connection.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        success = db.connect()
        if success:
            logger.info("Database initialized successfully")
        else:
            logger.error("Database initialization failed")
        return success
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False


async def cleanup_database():
    """
    Clean up database connections.
    """
    try:
        db.disconnect()
        logger.info("Database cleanup completed")
    except Exception as e:
        logger.error(f"Database cleanup error: {str(e)}")


def get_database() -> SupabaseDatabase:
    """
    Get the global database instance.
    
    Returns:
        SupabaseDatabase: The database instance
    """
    return db


async def get_booking_context_by_call_sid(call_sid: str) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive booking context data by Twilio callSid.
    Returns a dictionary with user_settings, agent, campaign, contact, user_profile, call_history, and booking_settings.
    """
    print(f"DEBUG: get_booking_context_by_call_sid called with call_sid: {call_sid}")
    logger.info(f"get_booking_context_by_call_sid: Initiated for call_sid: {call_sid}")
    if not db.is_connected():
        print(f"DEBUG: Database not connected")
        logger.error("Database not connected")
        return None
    
    try:
        async with db.get_connection() as client:
            try:
                logger.info(f"Calling RPC 'get_user_settings_by_callsid' with call_sid: {call_sid}")
                result = client.rpc('get_user_settings_by_callsid', {'p_call_sid': call_sid}).execute()
                logger.info(f"RPC result: {result}")

                # Check if we got data back
                if result.data and len(result.data) > 0:
                    context = result.data[0]
                    logger.info(f"Found booking context data with keys: {context.keys()}")
                    return context  # Returns dict with user_settings, agent, campaign, etc.
                else:
                    logger.warning(f"No booking context found for call_sid: {call_sid}")
                    return None
                    
            except Exception as rpc_error:
                logger.error(f"RPC call failed: {str(rpc_error)}")
                return None
                
    except Exception as e:
        logger.error(f"Error fetching booking context for callSid {call_sid}: {str(e)}")
        return None


async def validate_and_refresh_gcal_token(user_id: str, user_settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate Google Calendar token and refresh if necessary.
    
    Args:
        user_id: The user ID
        user_settings: User settings containing calendar integration data
        
    Returns:
        Dict containing valid token data, or None if validation/refresh fails
    """
    if not db.is_connected():
        logger.error("Database not connected")
        return None
    
    try:
        # Check if primary calendar integration is Google Calendar
        primary_integration = user_settings.get('primary_calendar_integration')
        if primary_integration != 'google_calendar':
            logger.info(f"Primary calendar integration is not Google Calendar: {primary_integration}")
            return None
        
        # Get Google Calendar integration settings
        integration_settings = user_settings.get('integration_settings', {})
        calendar_settings = integration_settings.get('calendar', {})
        gcal_settings = calendar_settings.get('google_calendar', {})
        
        if not gcal_settings:
            logger.warning(f"No Google Calendar settings found for user {user_id}")
            return None
        
        # Check token expiration
        created_at = gcal_settings.get('created_at')
        expires_in = gcal_settings.get('expires_in')
        
        if not created_at or not expires_in:
            logger.warning(f"Missing token timing data for user {user_id}")
            return None
        
        # Calculate token expiration (with 120 second buffer)
        import dateutil.parser
        
        created_time = dateutil.parser.parse(created_at)
        expires_in_seconds = int(expires_in)  # Convert to int in case it's a string
        expiration_time = created_time.timestamp() + (expires_in_seconds - 120)
        current_time = datetime.now(timezone.utc).timestamp()
        
        if current_time < expiration_time:
            # Token is still valid
            logger.info(f"Google Calendar token is valid for user {user_id}")
            return gcal_settings
        else:
            # Token needs refresh
            logger.info(f"Google Calendar token expired for user {user_id}, attempting refresh")
            
            refresh_token = gcal_settings.get('refresh_token')
            if not refresh_token:
                logger.error(f"No refresh token available for user {user_id}")
                return None
            
            # Refresh the token
            new_token_data = await refresh_google_calendar_token(refresh_token)
            
            if new_token_data:
                # Update the database with new token
                await update_gcal_credentials(user_id, new_token_data)
                return new_token_data
            else:
                logger.error(f"Failed to refresh Google Calendar token for user {user_id}")
                return None
                
    except Exception as e:
        logger.error(f"Error validating Google Calendar token for user {user_id}: {str(e)}")
        return None


async def refresh_google_calendar_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """
    Refresh Google Calendar access token using refresh token.
    
    Args:
        refresh_token: The refresh token
        
    Returns:
        Dict containing new token data, or None if refresh fails
    """
    import httpx
    from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    
    try:
        # Check if required OAuth credentials are available
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            logger.error("Missing Google OAuth credentials (GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET)")
            return None
        
        # Google OAuth2 token refresh endpoint
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            
            if response.status_code != 200:
                # Log detailed error information
                try:
                    error_data = response.json()
                    logger.error(f"Google OAuth error: {error_data}")
                except:
                    logger.error(f"Google OAuth error: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            token_data = response.json()
            
            # Add created_at timestamp for expiration calculation
            from datetime import datetime, timezone
            
            # Return the new token data
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': refresh_token,  # Refresh token usually stays the same
                'expires_in': token_data.get('expires_in', 3600),
                'scope': token_data.get('scope', ''),
                'token_type': token_data.get('token_type', 'Bearer'),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error refreshing Google Calendar token: {str(e)}")
        return None


async def update_gcal_credentials(user_id: str, token_data: Dict[str, Any]) -> bool:
    """
    Update Google Calendar credentials in the database.
    
    Args:
        user_id: The user ID
        token_data: New token data
        
    Returns:
        True if update successful, False otherwise
    """
    if not db.is_connected():
        logger.error("Database not connected")
        return False
    
    try:
        async with db.get_connection() as client:
            # Use Supabase RPC to execute the update query
            try:
                result = client.rpc('update_gcal_credentials', {
                    'p_user_id': user_id,
                    'p_access_token': token_data.get('access_token'),
                    'p_refresh_token': token_data.get('refresh_token'),
                    'p_expires_in': token_data.get('expires_in'),
                    'p_scope': token_data.get('scope'),
                    'p_token_type': token_data.get('token_type')
                }).execute()
                
                logger.info(f"Successfully updated Google Calendar credentials for user {user_id}")
                return True
                
            except Exception as rpc_error:
                logger.warning(f"RPC call failed, trying direct update: {str(rpc_error)}")
                
                # Fallback: direct table update
                update_data = {
                    'integration_settings': {
                        'calendar': {
                            'google_calendar': {
                                'access_token': token_data.get('access_token'),
                                'refresh_token': token_data.get('refresh_token'),
                                'expires_in': token_data.get('expires_in'),
                                'created_at': datetime.now(timezone.utc).isoformat(),
                                'scope': token_data.get('scope'),
                                'token_type': token_data.get('token_type')
                            }
                        }
                    }
                }
                
                result = client.table('user_settings').update(update_data).eq('user_id', user_id).execute()
                
                if result.data:
                    logger.info(f"Successfully updated Google Calendar credentials for user {user_id} using fallback")
                    return True
                else:
                    logger.error(f"Failed to update Google Calendar credentials for user {user_id}")
                    return False
                
    except Exception as e:
        logger.error(f"Error updating Google Calendar credentials for user {user_id}: {str(e)}")
        return False


async def create_google_calendar_event(
    token_data: Dict[str, Any],
    attendee: Dict[str, Any],
    time_utc: str,
    phone_number: Optional[str] = None,
    duration_minutes: int = 60
) -> Optional[Dict[str, Any]]:
    """
    Create an event in Google Calendar using the Google Calendar API.
    
    Args:
        token_data: Valid Google Calendar token data
        attendee: Dictionary containing attendee details (first_name, last_name, email, address)
        time_utc: Event start time in ISO 8601 format
        phone_number: Phone number to include in description
        duration_minutes: Event duration in minutes (default: 60)
        
    Returns:
        Dict containing event data if successful, None if failed
    """
    import httpx
    from datetime import timedelta
    import dateutil.parser
    
    try:
        access_token = token_data.get('access_token')
        if not access_token:
            logger.error("No access token available for Google Calendar")
            return None
        
        # Parse the start time and calculate end time
        start_datetime = dateutil.parser.parse(time_utc)
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        
        # Build description
        description = f"Phone: {phone_number}" if phone_number else ""
        
        # Prepare event data
        event_data = {
            'summary': f"Appointment with {attendee.get('first_name', '')} {attendee.get('last_name', '')}".strip(),
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'UTC'
            },
            'attendees': []
        }
        
        # Add attendee email if available
        email = attendee.get('email')
        if email:
            event_data['attendees'].append({
                'email': email,
                'displayName': f"{attendee.get('first_name', '')} {attendee.get('last_name', '')}".strip()
            })
        else:
            # Use default email if not provided
            event_data['attendees'].append({
                'email': 'unknown@chimelabs.ai'
            })
        
        # Add location if address is available
        if attendee.get('address'):
            event_data['location'] = attendee['address']
        
        # Make API call to Google Calendar
        headers = {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                json=event_data,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                event_result = response.json()
                logger.info(f"Successfully created Google Calendar event: {event_result.get('id')}")
                return event_result  # Return full event data
            else:
                logger.error(f"Failed to create Google Calendar event: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error creating Google Calendar event: {str(e)}")
        return None


async def store_event_booking(
    user_id: str,
    contact_id: Optional[str],
    event_data: Dict[str, Any],
    source: str = "google_calendar"
) -> Optional[str]:
    """
    Store booking record in event_bookings table.
    
    Args:
        user_id: User ID
        contact_id: Contact ID (optional)
        event_data: Event data from Google Calendar API
        source: Source of booking (default: "google_calendar")
        
    Returns:
        Booking ID if successful, None if failed
    """
    if not db.is_connected():
        logger.error("Database not connected")
        return None
    
    try:
        async with db.get_connection() as client:
            booking_data = {
                'title': event_data.get('summary', ''),
                'description': event_data.get('description', ''),
                'location': event_data.get('location', ''),
                'start_time': event_data.get('start', {}).get('dateTime'),
                'end_time': event_data.get('end', {}).get('dateTime'),
                'user_id': user_id,
                'contact_id': contact_id,
                'source': source,
                'source_booking_id': event_data.get('id'),
                'source_created_at': event_data.get('created'),
                'source_updated_at': event_data.get('updated'),
                'source_data': event_data
            }
            
            result = client.table('event_bookings').insert(booking_data).execute()
            
            if result.data and len(result.data) > 0:
                booking_id = result.data[0].get('id')
                logger.info(f"Successfully stored event booking: {booking_id}")
                return booking_id
            else:
                logger.error("Failed to store event booking")
                return None
                
    except Exception as e:
        logger.error(f"Error storing event booking: {str(e)}")
        return None


async def update_call_history_booking(
    call_sid: str,
    event_booking_id: str
) -> bool:
    """
    Update call_history with booking outcome.
    
    Args:
        call_sid: Twilio call SID
        event_booking_id: Event booking ID from event_bookings table
        
    Returns:
        True if successful, False otherwise
    """
    if not db.is_connected():
        logger.error("Database not connected")
        return False
    
    try:
        async with db.get_connection() as client:
            update_data = {
                'call_outcome': 'Booked',
                'event_booking_id': event_booking_id
            }
            
            result = client.table('call_history').update(update_data).eq('twilio_callsid', call_sid).execute()
            
            if result.data:
                logger.info(f"Successfully updated call_history for call_sid: {call_sid}")
                return True
            else:
                logger.error(f"Failed to update call_history for call_sid: {call_sid}")
                return False
                
    except Exception as e:
        logger.error(f"Error updating call_history: {str(e)}")
        return False
