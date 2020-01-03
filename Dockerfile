FROM python:3.7-stretch

# prevents stdout logging issues in docker
ENV PYTHONUNBUFFERED 1

# copy & install requirements first, as fairly static. This way, changes to code base, which init a new setup.py install,
# go a little faster as dependencies already installed.
COPY requirements.txt ./

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /

RUN python3 setup.py install

WORKDIR /dropboxs3

# no need for a CMD, well spawn various celery processes from docker-compose.yml instead
