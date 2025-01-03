import glob
from pathlib import Path

import nox
from nox.command import CommandFailed
from nox_poetry import session as poetry_session

# default test sessions - skips mypy & flake8 (for now...)
# lint checks whether code is in black format; blacken fixes any issues that might set off lint.
nox.options.sessions = ["isort", "black", "unit", "cover"]

# As long as these util versions are defined in pyproject.toml, no need to specify version here also.
BLACK_VERSION = "black"
ISORT_VERSION = "isort"
MYPY_VERSION = "mypy"

MYPY_TYPE_STUBS = [
    # "types-jsonschema",
    # "types-psutil",
    # "types-redis",
    # "types-requests",
    # "types-PyMySQL",
]

# don't define versions here, pyproject.toml has the version.
# "pytest-xdist",
# UNIT_TEST_STANDARD_DEPENDENCIES = [
#     "factory-boy",
#     "fakeldap",
#     "mock",
#     "moto",
#     "pytest",
#     "pytest-celery",
#     "pytest-cov",
#     "pytest-django",
#     "responses",
# ]

# FLAKE8_DEPENDENCIES = [
#     "Flake8-pyproject==1.2.3",
#     "flake8-django==1.4",
# ]

DEFAULT_PYTHON_VERSION = "3.12"
UNIT_TEST_PYTHON_VERSIONS = ["3.12"]

LINT_PATHS = [
    "dropboxs3",
    "noxfile.py",
    "tests",
]


@nox.session(python=DEFAULT_PYTHON_VERSION)
def blacken(session: nox.session):
    """
    Fixes linting problems. Make sure to run this before the lint step.
    """
    session.install(BLACK_VERSION)
    session.run("black", *LINT_PATHS)


@nox.session(python=DEFAULT_PYTHON_VERSION)
def isort(session: nox.session):
    """
    Checks if imports are ordered.
    """
    session.install(ISORT_VERSION)
    session.run("isort", *LINT_PATHS)


@nox.session(python=DEFAULT_PYTHON_VERSION)
def black(session: nox.session):
    """
    Checks for linting problems.
    """
    session.install(BLACK_VERSION)
    try:
        session.run("black", "--check", *LINT_PATHS)
    except CommandFailed:
        session.error("black check failed - have you run `nox -s blacken` ?")


@nox.session(python=DEFAULT_PYTHON_VERSION)
def flake8(session: nox.session):
    """
    flake8 checks. Ignores tests/ dir
    """
    session.install(*FLAKE8_DEPENDENCIES)
    session.run("flake8", *LINT_PATHS)


@poetry_session()
def unit(session: poetry_session):
    """
    Runs unit tests in tests/
    Uses a nox_poetry session, which ensures deps are installed as per the poetry.lock file
    """
    session.install(*UNIT_TEST_STANDARD_DEPENDENCIES)
    session.install(".")
    session.run(
        "py.test",
        *session.posargs,
    )
    session.notify("unit_test_cleanup")


@nox.session(python=DEFAULT_PYTHON_VERSION)
def cover(session: nox.session):
    """Run the final coverage report.

    This outputs the coverage report aggregating coverage from the unit
    test runs (not system test runs), and then erases coverage data.
    """
    session.install("coverage", "pytest-cov")
    session.run("coverage", "report")
    session.run("coverage", "erase")


@nox.session(python=DEFAULT_PYTHON_VERSION)
def mypy(session: nox.session):
    """
    Experimental mypy type checking
    """
    session.install(MYPY_VERSION, *MYPY_TYPE_STUBS)
    session.run("mypy", *session.posargs)


@nox.session(python=False)
def unit_test_cleanup(_: nox.session):
    """
    Clean up logs, dist/wheels, etc.
    """
    for filepath in [
        "local.gunicorn.access.log",
        "local.log",
        "nopodname.log",
        *glob.glob("dist/*.whl"),
    ]:
        Path(filepath).unlink(missing_ok=True)
