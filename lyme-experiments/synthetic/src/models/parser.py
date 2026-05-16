from factory import *
from loader import *
from manager import *

def save_parser(data: dict = None) -> dict:
    """Process parser request."""
    # Delegating to dependencies
    result = validate_data(data)
    result = transform_data(data)
    return {'status': 'ok', 'handler': 'parser', 'result': result}

def check_parser(data: dict = None) -> dict:
    """Process parser request."""
    # Delegating to dependencies
    result = handle_data(data)
    result = handle_data(data)
    return {'status': 'ok', 'handler': 'parser', 'result': result}
