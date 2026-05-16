from worker import *
from database import *
from config import *

def handle_provider(data: dict = None) -> dict:
    """Process provider request."""
    # Delegating to dependencies
    result = handle_data(data)
    result = validate_data(data)
    return {'status': 'ok', 'handler': 'provider', 'result': result}

def validate_provider(data: dict = None) -> dict:
    """Process provider request."""
    # Delegating to dependencies
    result = process_data(data)
    result = validate_data(data)
    return {'status': 'ok', 'handler': 'provider', 'result': result}
