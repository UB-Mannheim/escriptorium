# Installation

This document describes an installation into a [Debian-based](https://en.wikipedia.org/wiki/Category:Debian-based_distributions), Linux system such as [Ubuntu](https://ubuntu.com/), either running on a virtual machine or on real metal. The specific version this guide was tested with are [Ubuntu 18.04 LTS (Bionic Beaver)](https://releases.ubuntu.com/18.04/) and [Ubuntu 20.04 LTS (Focal Fossa)](https://releases.ubuntu.com/20.04/) as full installations, that is, not container-based installations of any sort. For an installation using [Docker](https://www.docker.com/), please refer to [the docker-install page on the Wiki](https://gitlab.com/scripta/escriptorium/-/wikis/docker-install). More generic installation instructions (but still for Debian-based distributions) are also available in [the full-install page on the Wiki](https://gitlab.com/scripta/escriptorium/-/wikis/full-install).

# System Requirements

The installation will probably not work with less than 4 GB of RAM. For running eScriptorium, you will want to have a minimum of 2 CPU cores available.

# Prerequisites

Ubuntu 18.04:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa # needed to get python > 3.7
sudo apt update
sudo apt install postgresql postgresql-contrib redis-server git libvips42 netcat-traditional jpegoptim pngcrush build-essential python3.8 python-dev python3-dev python3-virtualenv
```

Ubuntu 20.04:
```
sudo apt update
sudo apt install postgresql postgresql-contrib redis-server git libvips42 netcat-traditional jpegoptim pngcrush build-essential python3.8 python3.8-dev python3-virtualenv npm
```

Then:
```
sudo -i -u postgres /usr/bin/createuser --superuser $USER
createdb escriptorium
# psql escriptorium < backup-file.sql # if migrating from somewhere else
```

# Download and Configuration

```bash
git clone https://gitlab.com/scripta/escriptorium.git # will by default get you the "develop" branch
(
  cd escriptorium
  virtualenv env -p python3.8
  source env/bin/activate
  curl -sS https://bootstrap.pypa.io/get-pip.py | python
  python -m pip install -r app/requirements.txt
  cp app/escriptorium/local_settings.py{.example,}
  (
    cd front
    npm install
    npm run build
  )
)
echo "export PATH=\"$HOME/.local/bin:$PATH\" >> ~/.bashrc"
echo "export DJANGO_SETTINGS_MODULE=escriptorium.local_settings" >> ~/.bashrc
source ~/.bashrc
```

Now edit `escriptorium/app/escriptorium/local_settings.py` and at least out-comment anything related to `debug_toolbar` as well as `django_extensions`. If you did not follow the above instructions and kept the database role's name the same as your system user's name, database `USER`, and possibly `PASSWORD` as well might have to be commented-in and filled out.

## Everything Working?

```bash
(
  cd escriptorium/app
  python manage.py check
)
```

## Final Preparations

```bash
(
  cd escriptorium/app
  python manage.py migrate
  python manage.py createsuperuser # follow the prompts along
)
```

# Running a Development Server

```bash
(
  cd escriptorium/app
  celery -A escriptorium worker -l INFO &
  python manage.py runserver
)
```
