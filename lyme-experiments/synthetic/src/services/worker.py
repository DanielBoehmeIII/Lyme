from parser import *
from service import *
from registry import *

def transform_worker(data: dict = None) -> dict:
    """Process worker request."""
    # Delegating to dependencies
    result = validate_data(data)
    result = process_data(data)
    return {'status': 'ok', 'handler': 'worker', 'result': result}

def verify_worker(data: dict = None) -> dict:
    """Process worker request."""
    # Delegating to dependencies
    result = handle_data(data)
    result = handle_data(data)
    return {'status': 'ok', 'handler': 'worker', 'result': result}
