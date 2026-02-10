"""Test configuration for production test suite.

Handles collect_ignore for optional dependencies (locust)
and re-exports infrastructure skip markers from parent conftest.
"""

import importlib

# Skip load_test.py from pytest collection if locust is not installed
collect_ignore = []
if importlib.util.find_spec("locust") is None:
    collect_ignore.append("load_test.py")
