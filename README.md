### Docker
Install git, docker and docker-compose  
Fetch the source:  
> $ git clone git@gitlab.inria.fr:scripta/escriptorium.git  

Copy the environement variables file  
> $ cd escriptorium && cp variables.env_example variables.env  

change some of those if you wish to  
Build and run the docker containers  
> $ docker-compose up -d --build  
  
You should be able to access the website at http://localhost:8080/  
  
  
### Dev (without docker)  
Install in your environment of choice  
* postgresql, setup a user and create a database (default name is escriptorium)  
* redis  
* elasticsearch  
set max_map_count permanently  
> $ sudo sysctl -w vm.max_map_count=262144  
  
* env  
> $ virtualenv env -p /usr/bin/python3.7 (any version >= 3.5 should work)  
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
  
* if you need to test methods from the queue manager, set USE_CELERY=True and run a celery worker  
> $ celery -A app.escriptorium worker -l INFO  
  
* Create the sql tables  
> $ cd app && python manage.py migrate  

* Run the server  
> $ cd app && python manage.py runserver  

The website should be accessible at http://localhost:8000/  
