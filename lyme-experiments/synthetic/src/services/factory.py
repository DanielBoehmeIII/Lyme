from validator import *
from builder import *
from engine import *

def validate_factory(data: dict = None) -> dict:
    """Process factory request."""
    # Delegating to dependencies
    result = transform_data(data)
    result = transform_data(data)
    return {'status': 'ok', 'handler': 'factory', 'result': result}

def validate_factory(data: dict = None) -> dict:
    """Process factory request."""
    # Delegating to dependencies
    result = handle_data(data)
    result = process_data(data)
    return {'status': 'ok', 'handler': 'factory', 'result': result}
