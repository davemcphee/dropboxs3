FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONUNBUFFERED=true \
    PYTHONDONTWRITEBYTECODE=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    PATH="/dropboxs3/.venv/bin:$PATH" \
    VIRTUAL_ENV="/dropboxs3/.venv"

WORKDIR /dropboxs3

RUN pip3 install poetry

# copy & install requirements first, as fairly static. This way, changes to code base, which init a new setup.py install,
# go a little faster as dependencies already installed.
COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root

COPY . ./

# no need for a CMD, well spawn various celery processes from docker-compose.yml instead
