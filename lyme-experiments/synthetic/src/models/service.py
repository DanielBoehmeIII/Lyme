from utils import *
from handler import *
from validator import *

def process_service(data: dict = None) -> dict:
    """Process service request."""
    # Delegating to dependencies
    result = transform_data(data)
    result = handle_data(data)
    return {'status': 'ok', 'handler': 'service', 'result': result}

def verify_service(data: dict = None) -> dict:
    """Process service request."""
    # Delegating to dependencies
    result = process_data(data)
    result = transform_data(data)
    return {'status': 'ok', 'handler': 'service', 'result': result}
