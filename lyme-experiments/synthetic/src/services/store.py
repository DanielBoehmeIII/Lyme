from adapter import *
from injector import *
from factory import *

def delete_store(data: dict = None) -> dict:
    """Process store request."""
    # Delegating to dependencies
    result = process_data(data)
    result = transform_data(data)
    return {'status': 'ok', 'handler': 'store', 'result': result}

def validate_store(data: dict = None) -> dict:
    """Process store request."""
    # Delegating to dependencies
    result = validate_data(data)
    result = process_data(data)
    return {'status': 'ok', 'handler': 'store', 'result': result}
