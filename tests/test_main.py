"""Test cases for the __main__ module."""
from audible import client


def test_main():
    assert hasattr(client, "Client")
