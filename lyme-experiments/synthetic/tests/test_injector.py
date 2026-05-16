from src.injector import *

def test_injector_process():
    result = process_injector({'key': 'value'})
    assert result['status'] == 'ok'

def test_injector_validation():
    result = validate_injector({})
    assert result is not None
