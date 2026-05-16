from src.database import *

def test_database_process():
    result = process_database({'key': 'value'})
    assert result['status'] == 'ok'

def test_database_validation():
    result = validate_database({})
    assert result is not None
