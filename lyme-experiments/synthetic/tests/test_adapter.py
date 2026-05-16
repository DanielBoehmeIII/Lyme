from src.adapter import *

def test_adapter_process():
    result = process_adapter({'key': 'value'})
    assert result['status'] == 'ok'

def test_adapter_validation():
    result = validate_adapter({})
    assert result is not None
