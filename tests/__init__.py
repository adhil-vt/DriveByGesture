"""
gesturedrive.tests
==================
Test suite root.

Structure
---------
tests/unit/         Pure unit tests — one test file per module
tests/integration/  Multi-component pipeline tests
tests/fixtures/     Recorded landmark/profile data for parameterized tests
conftest.py         Shared pytest fixtures

Running
-------
    pytest tests/                      # all tests
    pytest tests/unit/                 # unit only
    pytest tests/ --cov=. --cov-report=term-missing
"""
