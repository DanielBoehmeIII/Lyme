from src.worker import *

def test_worker_process():
    result = process_worker({'key': 'value'})
    assert result['status'] == 'ok'

def test_worker_validation():
    result = validate_worker({})
    assert result is not None
