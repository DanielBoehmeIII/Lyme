from src.factory import *

def test_factory_process():
    result = process_factory({'key': 'value'})
    assert result['status'] == 'ok'

def test_factory_validation():
    result = validate_factory({})
    assert result is not None
