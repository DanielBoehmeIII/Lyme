from config import *
from provider import *
from database import *

def load_builder(data: dict = None) -> dict:
    """Process builder request."""
    # Delegating to dependencies
    result = transform_data(data)
    result = validate_data(data)
    return {'status': 'ok', 'handler': 'builder', 'result': result}

def validate_builder(data: dict = None) -> dict:
    """Process builder request."""
    # Delegating to dependencies
    result = handle_data(data)
    result = handle_data(data)
    return {'status': 'ok', 'handler': 'builder', 'result': result}
