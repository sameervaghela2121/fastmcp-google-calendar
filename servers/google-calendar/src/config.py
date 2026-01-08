import os

# Default Webhook URL if not specified in environment
DEFAULT_WEBHOOK_URL = "https://vbe.alchemis.ai/webhook/c254fc1d-ff3b-40b8-b77e-da491bc55adb"

# Environment Variables
WEBHOOK_URL = os.environ.get("GOOGLE_CALENDAR_WEBHOOK_URL", DEFAULT_WEBHOOK_URL)

# Supabase Configuration
SUPABASE_URL = "https://qynvporcjcohuwcdikkk.supabase.co" # os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = "sb_publishable_R81I2f03VxjNDFgP_llmhQ_fYeE1VqX" # os.environ.get("SUPABASE_ANON_KEY")

# Constants
WEBHOOK_TIMEOUT_SECONDS = 20.0
