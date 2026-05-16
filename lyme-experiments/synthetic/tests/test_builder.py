from src.builder import *

def test_builder_process():
    result = process_builder({'key': 'value'})
    assert result['status'] == 'ok'

def test_builder_validation():
    result = validate_builder({})
    assert result is not None
