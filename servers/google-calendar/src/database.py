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

logger = logging.getLogger(__name__)


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


async def get_booking_context_by_callsid(callsid: str) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive booking context data by Twilio callSid.
    
    This method executes a complex query that joins multiple tables to get:
    - User settings (including calendar integration API key)
    - Agent information
    - Campaign details
    - Contact information
    - User profile
    - Call history
    - Booking settings
    
    Args:
        callsid: The Twilio call SID to look up
        
    Returns:
        Dict containing all the booking context data, or None if not found
    """
    if not db.is_connected():
        logger.error("Database not connected")
        return None
    
    try:
        async with db.get_connection() as client:
            # Use Supabase RPC to call a stored procedure that executes the complex query
            # First, let's try to call a stored procedure named 'get_booking_context'
            try:
                result = client.rpc('get_booking_context', {'call_sid_param': callsid}).execute()
                
                if result.data and len(result.data) > 0:
                    booking_context = result.data[0]
                    logger.info(f"Successfully retrieved booking context for callSid: {callsid}")
                    return booking_context
                else:
                    logger.warning(f"No booking context found for callSid: {callsid}")
                    return None
                    
            except Exception as rpc_error:
                logger.warning(f"RPC call failed, trying alternative approach: {str(rpc_error)}")
                
                # Alternative approach: Build the query step by step using Supabase's query builder
                # This is a simplified version - you may need to adjust based on your exact schema
                
                # First, get the call history record
                call_result = client.table('call_history').select('*').eq('twilio_callsid', callsid).execute()
                
                if not call_result.data:
                    logger.warning(f"No call history found for callSid: {callsid}")
                    return None
                
                call_data = call_result.data[0]
                customer_id = call_data.get('customer_id')
                campaign_id = call_data.get('campaign_id')
                contact_id = call_data.get('contact_id')
                
                # Build the context by fetching related data
                context = {
                    'call_history': call_data
                }
                
                # Get user settings
                if customer_id:
                    user_settings_result = client.table('user_settings').select('*').eq('user_id', customer_id).execute()
                    if user_settings_result.data:
                        user_settings = user_settings_result.data[0]
                        context['user_settings'] = user_settings
                        # Extract API key from cal_integration JSON field
                        cal_integration = user_settings.get('cal_integration', {})
                        if isinstance(cal_integration, dict):
                            context['apiKey'] = cal_integration.get('apiKey')
                
                # Get campaign data
                if campaign_id:
                    campaign_result = client.table('campaigns').select('*').eq('id', campaign_id).execute()
                    if campaign_result.data:
                        context['campaign'] = campaign_result.data[0]
                        
                        # Get agent data
                        agent_id = campaign_result.data[0].get('agent_id')
                        if agent_id:
                            agent_result = client.table('agents').select('*').eq('id', agent_id).execute()
                            if agent_result.data:
                                context['agent'] = agent_result.data[0]
                
                # Get user profile
                if customer_id:
                    profile_result = client.table('user_profiles').select('*').eq('user_id', customer_id).execute()
                    if profile_result.data:
                        user_profile = profile_result.data[0]
                        context['user_profile'] = user_profile
                        
                        # Get company profile and booking settings
                        company_profile_id = user_profile.get('company_profile_id')
                        if company_profile_id:
                            company_result = client.table('company_profiles').select('booking_settings').eq('id', company_profile_id).execute()
                            if company_result.data:
                                context['booking_settings'] = company_result.data[0].get('booking_settings')
                
                # Get contact data
                if contact_id:
                    contact_result = client.table('campaign_contacts').select('*').eq('id', contact_id).execute()
                    if contact_result.data:
                        context['contact'] = contact_result.data[0]
                
                logger.info(f"Successfully retrieved booking context for callSid: {callsid} using fallback method")
                return context
                
    except Exception as e:
        logger.error(f"Error fetching booking context for callSid {callsid}: {str(e)}")
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
        from datetime import datetime, timezone
        import dateutil.parser
        
        created_time = dateutil.parser.parse(created_at)
        expiration_time = created_time.timestamp() + (expires_in - 120)
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
            
            # Refresh the token (you'll need to implement the actual OAuth refresh logic)
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
            response.raise_for_status()
            
            token_data = response.json()
            
            # Return the new token data
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': refresh_token,  # Refresh token usually stays the same
                'expires_in': token_data.get('expires_in', 3600),
                'scope': token_data.get('scope', ''),
                'token_type': token_data.get('token_type', 'Bearer')
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
    description: Optional[str] = None,
    duration_minutes: int = 60
) -> Optional[Dict[str, Any]]:
    """
    Create an event in Google Calendar using the Google Calendar API.
    
    Args:
        token_data: Valid Google Calendar token data
        attendee: Dictionary containing attendee details
        time_utc: Event start time in ISO 8601 format
        description: Event description
        duration_minutes: Event duration in minutes (default: 60)
        
    Returns:
        Dict containing event data if successful, None if failed
    """
    import httpx
    from datetime import datetime, timedelta
    import dateutil.parser
    
    try:
        access_token = token_data.get('access_token')
        if not access_token:
            logger.error("No access token available for Google Calendar")
            return None
        
        # Parse the start time and calculate end time
        start_datetime = dateutil.parser.parse(time_utc)
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        
        # Prepare event data
        event_data = {
            'summary': f"Appointment with {attendee.get('first_name', '')} {attendee.get('last_name', '')}".strip(),
            'description': description or f"Appointment for {attendee.get('first_name', '')} {attendee.get('last_name', '')}".strip(),
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
        if attendee.get('email'):
            event_data['attendees'].append({
                'email': attendee['email'],
                'displayName': f"{attendee.get('first_name', '')} {attendee.get('last_name', '')}".strip()
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
                return {
                    'event_id': event_result.get('id'),
                    'html_link': event_result.get('htmlLink'),
                    'status': event_result.get('status'),
                    'summary': event_result.get('summary'),
                    'start': event_result.get('start'),
                    'end': event_result.get('end')
                }
            else:
                logger.error(f"Failed to create Google Calendar event: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error creating Google Calendar event: {str(e)}")
        return None
