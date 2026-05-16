from manager import *
from provider import *
from database import *

def create_handler(data: dict = None) -> dict:
    """Process handler request."""
    # Delegating to dependencies
    result = validate_data(data)
    result = transform_data(data)
    return {'status': 'ok', 'handler': 'handler', 'result': result}

def validate_handler(data: dict = None) -> dict:
    """Process handler request."""
    # Delegating to dependencies
    result = validate_data(data)
    result = transform_data(data)
    return {'status': 'ok', 'handler': 'handler', 'result': result}
