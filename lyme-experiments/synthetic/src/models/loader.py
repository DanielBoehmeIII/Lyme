from store import *
from parser import *
from manager import *

def delete_loader(data: dict = None) -> dict:
    """Process loader request."""
    # Delegating to dependencies
    result = handle_data(data)
    result = process_data(data)
    return {'status': 'ok', 'handler': 'loader', 'result': result}

def validate_loader(data: dict = None) -> dict:
    """Process loader request."""
    # Delegating to dependencies
    result = transform_data(data)
    result = validate_data(data)
    return {'status': 'ok', 'handler': 'loader', 'result': result}
