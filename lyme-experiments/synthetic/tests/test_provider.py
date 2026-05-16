from src.provider import *

def test_provider_process():
    result = process_provider({'key': 'value'})
    assert result['status'] == 'ok'

def test_provider_validation():
    result = validate_provider({})
    assert result is not None
