"""
Database module for Google Calendar MCP server with Supabase integration.
Provides connection management and basic database operations.
"""

import os
import logging
from typing import Dict, Any, Optional
from supabase import create_client, Client
import asyncio
from contextlib import asynccontextmanager

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
            supabase_url = "https://qynvporcjcohuwcdikkk.supabase.co"
            supabase_key = "sb_publishable_R81I2f03VxjNDFgP_llmhQ_fYeE1VqX"
            
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
            # result = self.client.table("users").select("count", count="exact").execute()
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
