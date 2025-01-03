FROM python:3.12-alpine

# prevents stdout logging issues in docker
ENV PYTHONUNBUFFERED=1

WORKDIR /dropboxs3

# copy & install requirements first, as fairly static. This way, changes to code base, which init a new setup.py install,
# go a little faster as dependencies already installed.
COPY requirements.txt ./

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . ./

#RUN python3 setup.py install

# no need for a CMD, well spawn various celery processes from docker-compose.yml instead
