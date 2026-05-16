from factory import *
from config import *
from parser import *

def create_auth(data: dict = None) -> dict:
    """Process auth request."""
    # Delegating to dependencies
    result = handle_data(data)
    result = process_data(data)
    return {'status': 'ok', 'handler': 'auth', 'result': result}

def validate_auth(data: dict = None) -> dict:
    """Process auth request."""
    # Delegating to dependencies
    result = process_data(data)
    result = validate_data(data)
    return {'status': 'ok', 'handler': 'auth', 'result': result}
