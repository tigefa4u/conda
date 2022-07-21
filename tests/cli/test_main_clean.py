# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from datetime import datetime
from json import loads as json_loads
from os import walk
from os.path import basename, isdir, join, exists
from shutil import copy
from conda.base.constants import CONDA_PACKAGE_EXTENSIONS, CONDA_TEMP_EXTENSIONS, CONDA_LOGS_DIR
from conda.core.subdir_data import create_cache_dir
from conda.gateways.disk.create import mkdir_p
from conda.testing.integration import make_temp_package_cache, run_command, Commands, make_temp_env

def _get_pkgs(pkgs_dir):
    _, dirs, _ = next(walk(pkgs_dir))
    return [join(pkgs_dir, pkg) for pkg in dirs]


def _get_tars(pkgs_dir):
    _, _, files = next(walk(pkgs_dir))
    return [join(pkgs_dir, file) for file in files if file.endswith(CONDA_PACKAGE_EXTENSIONS)]


def _get_index_cache():
    cache_dir = create_cache_dir()
    _, _, files = next(walk(cache_dir))
    return [join(cache_dir, file) for file in files if file.endswith(".json")]


def _get_tempfiles(pkgs_dir):
    _, _, files = next(walk(pkgs_dir))
    return [join(pkgs_dir, file) for file in files if file.endswith(CONDA_TEMP_EXTENSIONS)]


def _get_logfiles(pkgs_dir):
    root, _, files = next(walk(join(pkgs_dir, CONDA_LOGS_DIR)), [None, None, []])
    return [join(root, file) for file in files]


def _get_all(pkgs_dir):
    return _get_pkgs(pkgs_dir), _get_tars(pkgs_dir), _get_index_cache()


def assert_any_pkg(name, contents):
    assert any(basename(content).startswith(f"{name}-") for content in contents)


def assert_not_pkg(name, contents):
    assert not any(basename(content).startswith(f"{name}-") for content in contents)


# conda clean --force-pkgs-dirs
def test_clean_force_pkgs_dirs(clear_cache):
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # pkgs_dir is a directory
        assert isdir(pkgs_dir)

        with make_temp_env(pkg):
            stdout, _, _ = run_command(Commands.CLEAN, "", "--force-pkgs-dirs", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # pkgs_dir is removed
            assert not exists(pkgs_dir)

        # pkgs_dir is still removed
        assert not exists(pkgs_dir)


# conda clean --packages
def test_clean_and_packages(clear_cache):
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # pkg doesn't exist ahead of time
        assert_not_pkg(pkg, _get_pkgs(pkgs_dir))

        with make_temp_env(pkg) as prefix:
            # pkg exists
            assert_any_pkg(pkg, _get_pkgs(pkgs_dir))

            # --json flag is regression test for #5451
            stdout, _, _ = run_command(Commands.CLEAN, "", "--packages", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # pkg still exists since its in use by temp env
            assert_any_pkg(pkg, _get_pkgs(pkgs_dir))

            run_command(Commands.REMOVE, prefix, pkg, "--yes", "--json")
            stdout, _, _ = run_command(Commands.CLEAN, "", "--packages", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # pkg is removed
            assert_not_pkg(pkg, _get_pkgs(pkgs_dir))

        # pkg is still removed
        assert_not_pkg(pkg, _get_pkgs(pkgs_dir))


# conda clean --tarballs
def test_clean_tarballs(clear_cache):
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # tarball doesn't exist ahead of time
        assert_not_pkg(pkg, _get_tars(pkgs_dir))

        with make_temp_env(pkg):
            # tarball exists
            assert_any_pkg(pkg, _get_tars(pkgs_dir))

            # --json flag is regression test for #5451
            stdout, _, _ = run_command(Commands.CLEAN, "", "--tarballs", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # tarball is removed
            assert_not_pkg(pkg, _get_tars(pkgs_dir))

        # tarball is still removed
        assert_not_pkg(pkg, _get_tars(pkgs_dir))


# conda clean --index-cache
def test_clean_index_cache(clear_cache):
    pkg = "bzip2"

    with make_temp_package_cache():
        # index cache doesn't exist ahead of time
        assert not _get_index_cache()

        with make_temp_env(pkg):
            # index cache exists
            assert _get_index_cache()

            stdout, _, _ = run_command(Commands.CLEAN, "", "--index-cache", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # index cache is cleared
            assert not _get_index_cache()

        # index cache is still cleared
        assert not _get_index_cache()


# conda clean --tempfiles
def test_clean_tempfiles(clear_cache):
    """Tempfiles are either suffixed with .c~ or .trash.

    .c~ is used to indicate that conda is actively using that file. If the conda process is
    terminated unexpectedly these .c~ files may remain and hence can be cleaned up after the fact.

    .trash appears to be a legacy suffix that is no longer used by conda.

    Since the presence of .c~ and .trash files are dependent upon irregular termination we create
    our own temporary files to confirm they get cleaned up.
    """
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # tempfiles don't exist ahead of time
        assert not _get_tempfiles(pkgs_dir)

        with make_temp_env(pkg):
            # mimic tempfiles being created
            path = _get_tars(pkgs_dir)[0]  # grab any tarball
            for ext in CONDA_TEMP_EXTENSIONS:
                copy(path, f"{path}{ext}")

            # tempfiles exist
            assert len(_get_tempfiles(pkgs_dir)) == len(CONDA_TEMP_EXTENSIONS)

            # --json flag is regression test for #5451
            stdout, _, _ = run_command(
                Commands.CLEAN, "", "--tempfiles", pkgs_dir, "--yes", "--json"
            )
            json_loads(stdout)  # assert valid json

            # tempfiles removed
            assert not _get_tempfiles(pkgs_dir)

        # tempfiles still removed
        assert not _get_tempfiles(pkgs_dir)


# conda clean --logfiles
def test_clean_logfiles(clear_cache):
    """Logfiles are found in pkgs_dir/.logs.

    Since these log files are uniquely implemented for the experimental libmamba release we will
    mock the log files.
    """
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # logfiles don't exist ahead of time
        assert not _get_logfiles(pkgs_dir)

        with make_temp_env(pkg):
            # mimic logfiles being created
            logs = join(pkgs_dir, CONDA_LOGS_DIR)
            mkdir_p(logs)
            path = join(logs, f"{datetime.utcnow():%Y%m%d-%H%M%S-%f}.log")
            with open(path, "w"):
                pass

            # logfiles exist
            assert path in _get_logfiles(pkgs_dir)

            # --json flag is regression test for #5451
            stdout, _, _ = run_command(Commands.CLEAN, "", "--logfiles", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # logfiles removed
            assert not _get_logfiles(pkgs_dir)

        # logfiles still removed
        assert not _get_logfiles(pkgs_dir)


# conda clean --all
def test_clean_all(clear_cache):
    pkg = "bzip2"

    with make_temp_package_cache() as pkgs_dir:
        # pkg, tarball, & index cache doesn't exist ahead of time
        pkgs, tars, cache = _get_all(pkgs_dir)
        assert_not_pkg(pkg, pkgs)
        assert_not_pkg(pkg, tars)
        assert not cache

        with make_temp_env(pkg) as prefix:
            # pkg, tarball, & index cache exists
            pkgs, tars, cache = _get_all(pkgs_dir)
            assert_any_pkg(pkg, pkgs)
            assert_any_pkg(pkg, tars)
            assert cache

            stdout, _, _ = run_command(Commands.CLEAN, "", "--all", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # pkg still exists since its in use by temp env
            # tarball is removed
            # index cache is cleared
            pkgs, tars, cache = _get_all(pkgs_dir)
            assert_any_pkg(pkg, pkgs)
            assert_not_pkg(pkg, tars)
            assert not cache

            run_command(Commands.REMOVE, prefix, pkg, "--yes", "--json")
            stdout, _, _ = run_command(Commands.CLEAN, "", "--packages", "--yes", "--json")
            json_loads(stdout)  # assert valid json

            # pkg is removed
            # tarball is still removed
            # index cache is still cleared
            pkgs, tars, index_cache = _get_all(pkgs_dir)
            assert_not_pkg(pkg, pkgs)
            assert_not_pkg(pkg, tars)
            assert not cache

        # pkg is still removed
        # tarball is still removed
        # index cache is still cleared
        pkgs, tars, index_cache = _get_all(pkgs_dir)
        assert_not_pkg(pkg, pkgs)
        assert_not_pkg(pkg, tars)
        assert not cache
