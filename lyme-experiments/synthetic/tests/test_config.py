from src.config import *

def test_config_process():
    result = process_config({'key': 'value'})
    assert result['status'] == 'ok'

def test_config_validation():
    result = validate_config({})
    assert result is not None
