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
Two options, [install with Docker](install-with-docker), or a [full local install](full-install).  
  
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


