import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Add shared utilities to Python path
shared_src_dir = current_dir.parent.parent / "shared" / "src"
sys.path.insert(0, str(shared_src_dir))

# Now import the functions
# from main import _book_appointment_logic, _check_availability_logic
from src.main import _book_appointment_logic, _check_availability_logic

async def test_booking():
    # Mock data based on Notion example
    attendee = {
        "phone_number": "+61403722371",
        "first_name": "Test",
        "last_name": "User",
        "address": "123 Test St, Testville",
        "email": "test@example.com"
    }
    time_utc = "2025-07-05T11:00:00+10:00"
    conversation_id = "test_conv_id_123"
    callSid = "test_call_sid_456"
    
    print("Testing check_availability...")
    try:
        availability = _check_availability_logic(
            start_date="2025-07-05T09:00:00+10:00",
            end_date="2025-07-12T09:00:00+10:00",
            conversation_id=conversation_id,
            callSid=callSid
        )
        print(f"Availability Result: {availability}")
    except Exception as e:
        print(f"Error during availability test: {e}")

    print("\nTesting book_appointment...")
    try:
        result = _book_appointment_logic(
            attendee=attendee,
            time_utc=time_utc,
            conversation_id=conversation_id,
            callSid=callSid
        )
        print(f"Booking Result: {result}")
    except Exception as e:
        print(f"Error during booking test: {e}")

if __name__ == "__main__":
    asyncio.run(test_booking())
