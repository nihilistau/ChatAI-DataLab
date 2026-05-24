# Workshop test suite

The Workshop layer now reuses the canonical shared test coverage. We removed the duplicate
placeholder modules (`test_lab_paths.py`, `test_metrics.py`, `test_search_telemetry.py`, `test_widgets.py`)
that previously shadowed the real module names and caused `pytest` import mismatches.

When you add Workshop-specific tests in the future, give each module a unique filename (for example
`test_workshop_lab_paths.py`) so the Python importer can distinguish them from the shared suites.
This keeps `python -m pytest` free of `import file mismatch` errors even when both stacks
share similar test names.
