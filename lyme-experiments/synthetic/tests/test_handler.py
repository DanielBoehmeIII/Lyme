from src.handler import *

def test_handler_process():
    result = process_handler({'key': 'value'})
    assert result['status'] == 'ok'

def test_handler_validation():
    result = validate_handler({})
    assert result is not None
