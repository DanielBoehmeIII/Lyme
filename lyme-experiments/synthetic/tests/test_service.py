from src.service import *

def test_service_process():
    result = process_service({'key': 'value'})
    assert result['status'] == 'ok'

def test_service_validation():
    result = validate_service({})
    assert result is not None
