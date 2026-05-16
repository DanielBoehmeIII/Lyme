from src.utils import *

def test_utils_process():
    result = process_utils({'key': 'value'})
    assert result['status'] == 'ok'

def test_utils_validation():
    result = validate_utils({})
    assert result is not None
