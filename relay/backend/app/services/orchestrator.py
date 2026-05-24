from __future__ import annotations

"""Shared orchestrator factory used across API modules."""

# @tag:backend,services,ops

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from controlplane import LabOrchestrator, get_default_orchestrator


_ORCHESTRATOR: LabOrchestrator = get_default_orchestrator()


def get_orchestrator() -> LabOrchestrator:
    """Return the singleton LabOrchestrator instance."""

    return _ORCHESTRATOR


def set_orchestrator(override: LabOrchestrator) -> None:
    """Allow tests to swap in a stub orchestrator."""

    global _ORCHESTRATOR
    _ORCHESTRATOR = override
