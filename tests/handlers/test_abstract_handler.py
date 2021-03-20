import pytest

from mangum.handlers import AbstractHandler


def test_abstract_handler_unkown_event():
    """
    Test an unknown event, ensure it fails in a consistent way
    """
    example_event = {"hello": "world", "foo": "bar"}
    example_context = {}
    with pytest.raises(TypeError):
        AbstractHandler.from_trigger(example_event, example_context)
