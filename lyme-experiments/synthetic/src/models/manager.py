from database import *
from injector import *
from registry import *

def create_manager(data: dict = None) -> dict:
    """Process manager request."""
    # Delegating to dependencies
    result = validate_data(data)
    result = validate_data(data)
    return {'status': 'ok', 'handler': 'manager', 'result': result}

def verify_manager(data: dict = None) -> dict:
    """Process manager request."""
    # Delegating to dependencies
    result = validate_data(data)
    result = handle_data(data)
    return {'status': 'ok', 'handler': 'manager', 'result': result}
