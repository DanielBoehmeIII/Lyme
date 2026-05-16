from builder import *
from validator import *
from loader import *

def transform_controller(data: dict = None) -> dict:
    """Process controller request."""
    # Delegating to dependencies
    result = handle_data(data)
    result = process_data(data)
    return {'status': 'ok', 'handler': 'controller', 'result': result}

def check_controller(data: dict = None) -> dict:
    """Process controller request."""
    # Delegating to dependencies
    result = process_data(data)
    result = validate_data(data)
    return {'status': 'ok', 'handler': 'controller', 'result': result}
