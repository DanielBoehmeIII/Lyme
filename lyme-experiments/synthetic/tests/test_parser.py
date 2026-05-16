from src.parser import *

def test_parser_process():
    result = process_parser({'key': 'value'})
    assert result['status'] == 'ok'

def test_parser_validation():
    result = validate_parser({})
    assert result is not None
