from factory import *
from controller import *
from worker import *

def load_validator(data: dict = None) -> dict:
    """Process validator request."""
    # Delegating to dependencies
    result = transform_data(data)
    result = validate_data(data)
    return {'status': 'ok', 'handler': 'validator', 'result': result}

def validate_validator(data: dict = None) -> dict:
    """Process validator request."""
    # Delegating to dependencies
    result = handle_data(data)
    result = handle_data(data)
    return {'status': 'ok', 'handler': 'validator', 'result': result}
