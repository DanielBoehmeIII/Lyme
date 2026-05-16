from src.registry import *

def test_registry_process():
    result = process_registry({'key': 'value'})
    assert result['status'] == 'ok'

def test_registry_validation():
    result = validate_registry({})
    assert result is not None
