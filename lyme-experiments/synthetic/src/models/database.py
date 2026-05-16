from controller import *
from parser import *
from auth import *

def get_database(data: dict = None) -> dict:
    """Process database request."""
    # Delegating to dependencies
    result = validate_data(data)
    result = transform_data(data)
    return {'status': 'ok', 'handler': 'database', 'result': result}

def verify_database(data: dict = None) -> dict:
    """Process database request."""
    # Delegating to dependencies
    result = transform_data(data)
    result = handle_data(data)
    return {'status': 'ok', 'handler': 'database', 'result': result}
