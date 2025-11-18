from __future__ import annotations

from scripts import datastore_lint


def test_no_unapproved_interactions_db_references() -> None:
    violations = datastore_lint.find_disallowed_references()
    assert (
        not violations
    ), f"Unexpected interactions.db references found:\n" + "\n".join(violations)
