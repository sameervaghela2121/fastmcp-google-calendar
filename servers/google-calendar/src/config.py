import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default Webhook URL if not specified in environment
DEFAULT_WEBHOOK_URL = "https://vbe.alchemis.ai/webhook/c254fc1d-ff3b-40b8-b77e-da491bc55adb"

# Environment Variables
WEBHOOK_URL = os.environ.get("GOOGLE_CALENDAR_WEBHOOK_URL", DEFAULT_WEBHOOK_URL)

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# Constants
WEBHOOK_TIMEOUT_SECONDS = 20.0
