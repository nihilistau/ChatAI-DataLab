from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat import validator


def normalize_notebook(source: Path, destination: Path | None = None) -> Path:
    """Return a normalized notebook copy with generated cell ids.

    Args:
        source: Path to the original .ipynb file.
        destination: Optional path for the normalized copy. When omitted,
            the source file is normalized in-place.
    """

    if destination is None:
        destination = source

    destination.parent.mkdir(parents=True, exist_ok=True)

    notebook = nbformat.read(source, as_version=nbformat.NO_CONVERT)
    validator.normalize(notebook)
    nbformat.write(notebook, destination)
    return destination
