import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def validate_config():
    """Validates that all required environment variables are set."""
    required_vars = ["GOOGLE_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var) or os.getenv(var) == "YOUR_API_KEY_HERE"]
    
    if missing_vars:
        raise ValueError(
            f"Missing or invalid environment variables: {', '.join(missing_vars)}. "
            f"Please check your backend/.env file."
        )

# Run validation on module import
validate_config()

# Export variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
