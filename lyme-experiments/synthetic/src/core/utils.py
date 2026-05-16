from registry import *
from parser import *
from loader import *

def process_utils(data: dict = None) -> dict:
    """Process utils request."""
    # Delegating to dependencies
    result = process_data(data)
    result = process_data(data)
    return {'status': 'ok', 'handler': 'utils', 'result': result}

def validate_utils(data: dict = None) -> dict:
    """Process utils request."""
    # Delegating to dependencies
    result = validate_data(data)
    result = process_data(data)
    return {'status': 'ok', 'handler': 'utils', 'result': result}
