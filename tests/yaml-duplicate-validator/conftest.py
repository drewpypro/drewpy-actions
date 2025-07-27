# conftest.py
def pytest_addoption(parser):
    parser.addoption(
        "--output-mode", action="store", default="actual",
        help="Diff output mode: actual, ndiff, unified, or all"
    )

import pytest

@pytest.fixture
def output_mode(request):
    return request.config.getoption("--output-mode")
