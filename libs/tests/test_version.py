from importlib.metadata import version

import cauth


def test_installed_version_is_the_module_version():
    # pyproject.toml reads __version__, so the two cannot drift (R31).
    assert version("cauth") == cauth.__version__
