from src.engine import *

def test_engine_process():
    result = process_engine({'key': 'value'})
    assert result['status'] == 'ok'

def test_engine_validation():
    result = validate_engine({})
    assert result is not None
