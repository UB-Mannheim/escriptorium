eScriptorium is part of the [scripta](https://www.psl.eu/en/scripta) project, its goal is provide researchers in the humanity field with an integrated set of tools to transcribe, annotate, translate and publish historical documents.  
The eScriptorium app itself is at the 'center'. It is a work in progress but will implement at least automatic transcriptions through kraken, indexation for complex search and filtering, annotation and some simple form of collaborative working (sharing, versioning)
  
## The stack
- nginx
- uwsgi
- [django](https://www.djangoproject.com/)
- [daphne](https://github.com/django/daphne) (channel server for websockets)
- [celery](http://www.celeryproject.org/)
- postgres
- [elasticsearch](https://www.elastic.co/) (integration not started yet)
- redis (cache, celery broker, other disposable data)
- [kraken](http://kraken.re)
- [docker](https://www.docker.com/) (deployment)
  
  
## The code
Following [CIA's coding guidelines](https://wikileaks.org/ciav7p1/cms/page_26607631.html) (It is just a well writen guidelines on top of PEP-8).  
All the templates are in the project folder, because templating is close to the project than the app, and the project is bound to the app through INSTALLED_APPS and urls, not the other way around.  
A more debatable decision is to let the javascript sources in their respective apps, they are very tightly bound to the markup so it would make sense that they live in the project space, but they also contain a fair amount of logic.
In the end, it was decided that it would be easier to keep a clean directory tree this way.  
  
  
## Install
#### Docker
Install git, docker and docker-compose  
Fetch the source:  
> $ git clone git@gitlab.inria.fr:scripta/escriptorium.git  
  
Copy the environement variables file  
> $ cd escriptorium && cp variables.env_example variables.env  
  
change some of those if you wish to  
Build and run the docker containers  
> $ docker-compose up -d --build  
   
You should be able to access the website at http://localhost:8080/  
  
To update:  
> $ git pull  
> $ docker-compose up -d --build  
  
#### Dev (without docker)  
Install in your environment of choice  
* postgresql, setup a user and create a database (default name is escriptorium)  
* redis  
* elasticsearch  
set max_map_count permanently  
> $ sudo sysctl -w vm.max_map_count=262144  
  
* env  
> $ virtualenv env -p python3.7 (any version >= 3.7 should work)  
> $ . env/bin/activate  
> $ pip install -r requirements.txt  
  
  
* if you want to use local settings the prefered way is to invoque manage.py with the --settings option  
For example local_settings.py  
```python
from escriptorium.settings import *  
  
# requires pip install django-debug-toolbar  
INSTALLED_APPS += ['debug_toolbar',]  
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware',]  
INTERNAL_IPS += ['127.0.0.1',]  
```  
  
it is recomanded to then make an alias for manage.py or set $DJANGO_SETTINGS_MODULE  
  
* To run a basic celery worker listening on everything  
> $ celery -A app.escriptorium worker -l INFO  
To disable celery you can set `CELERY_TASK_ALWAYS_EAGER = True`  

* Create the sql tables  
> $ cd app && python manage.py migrate  
  
* Run the server  
> $ cd app && python manage.py runserver  
  
The website should be accessible at http://localhost:8000/  


## Running tests

Simply run  
> $ python manage.py test  

To run the tests for a single app  
> $ python manage.py test api  
  
Or a single test (example)  
> $ python manage.py test api.tests.DocumentViewSetTestCase.test_list  
  
Coverage  
> $ coverage run --omit=*/env/* manage.py test  
> $ coverage report -m  


