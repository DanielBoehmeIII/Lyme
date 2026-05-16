from validator import *
from adapter import *
from manager import *

def load_registry(data: dict = None) -> dict:
    """Process registry request."""
    # Delegating to dependencies
    result = process_data(data)
    result = transform_data(data)
    return {'status': 'ok', 'handler': 'registry', 'result': result}

def validate_registry(data: dict = None) -> dict:
    """Process registry request."""
    # Delegating to dependencies
    result = transform_data(data)
    result = process_data(data)
    return {'status': 'ok', 'handler': 'registry', 'result': result}
