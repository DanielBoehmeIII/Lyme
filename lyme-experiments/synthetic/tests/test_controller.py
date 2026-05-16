from src.controller import *

def test_controller_process():
    result = process_controller({'key': 'value'})
    assert result['status'] == 'ok'

def test_controller_validation():
    result = validate_controller({})
    assert result is not None
