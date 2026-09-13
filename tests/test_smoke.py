"""Stage 0 smoke test: the package imports and exposes a version."""

import hanoi_crossing


def test_package_exposes_version() -> None:
    assert hanoi_crossing.__version__ == "0.1.0"
