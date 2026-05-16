from src.validator import *

def test_validator_process():
    result = process_validator({'key': 'value'})
    assert result['status'] == 'ok'

def test_validator_validation():
    result = validate_validator({})
    assert result is not None
