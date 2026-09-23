"""The package imports and reports the version its metadata declares."""

from importlib.metadata import version

import hanoi_crossing


def test_package_version_matches_its_metadata() -> None:
    assert hanoi_crossing.__version__ == version("hanoi-crossing")
