FROM python:3.12-slim

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=non-interactive

# set work directory
WORKDIR /usr/src/app

# Install base Debian packages
# and cleanup afterwards to reduce image size
RUN apt-get update -q && \
    apt-get -y -qq install --no-install-recommends netcat-traditional jpegoptim \
    pngcrush libvips libffi-dev git build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Install OpenJDK
RUN echo "Installing jvm" && \
    apt-get update && \
    apt-get install -y default-jre default-jdk && \
    apt-get install -y ant && \
    apt-get clean;

# Set JAVA_HOME
RUN export JAVA_HOME=$(dirname $(dirname $(readlink -f  /usr/bin/java)))

# Add non privileged user to run the app
RUN addgroup --system uwsgi
RUN adduser --system --no-create-home --ingroup uwsgi uwsgi

RUN pip install --root-user-action ignore -q --upgrade pip

# Install Python packages and remove cache
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip --no-cache-dir install --root-user-action ignore -q -r requirements.txt
