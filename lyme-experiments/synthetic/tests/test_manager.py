from src.manager import *

def test_manager_process():
    result = process_manager({'key': 'value'})
    assert result['status'] == 'ok'

def test_manager_validation():
    result = validate_manager({})
    assert result is not None
