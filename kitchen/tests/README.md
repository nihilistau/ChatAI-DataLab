# Kitchen test suite

The Kitchen layer now reuses the canonical `datalab/tests` coverage. We removed the duplicate
placeholder modules (`test_lab_paths.py`, `test_metrics.py`, `test_search_telemetry.py`, `test_widgets.py`)
that previously shadowed the real module names and caused `pytest` import mismatches.

When you add Kitchen-specific tests in the future, give each module a unique filename (for example
`test_kitchen_lab_paths.py`) so the Python importer can distinguish them from the shared Datalab
suites. This keeps `python -m pytest` free of `import file mismatch` errors even when both stacks
share similar test names.
