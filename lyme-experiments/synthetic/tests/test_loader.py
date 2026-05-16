from src.loader import *

def test_loader_process():
    result = process_loader({'key': 'value'})
    assert result['status'] == 'ok'

def test_loader_validation():
    result = validate_loader({})
    assert result is not None
