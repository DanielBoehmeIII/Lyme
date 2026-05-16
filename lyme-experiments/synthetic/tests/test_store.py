from src.store import *

def test_store_process():
    result = process_store({'key': 'value'})
    assert result['status'] == 'ok'

def test_store_validation():
    result = validate_store({})
    assert result is not None
