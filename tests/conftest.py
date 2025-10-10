import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests (tests marked with @pytest.mark.integration)",
    )
    parser.addoption(
        "--smoke",
        action="store_true",
        default=False,
        help="Run smoke tests (tests marked with @pytest.mark.smoke)",
    )

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "smoke: mark test as smoke test")

def pytest_collection_modifyitems(config, items):
    # Handle integration tests
    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(reason="Need --integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

    # Handle smoke tests
    if config.getoption("--smoke"):
        skip_non_smoke = pytest.mark.skip(reason="Skipped because not a smoke test")
        for item in items:
            if "smoke" not in item.keywords:
                item.add_marker(skip_non_smoke)