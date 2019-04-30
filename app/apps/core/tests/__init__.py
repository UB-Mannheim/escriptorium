from .views import DocumentTestCase
from .share import DocumentShareTestCase
from .process import DocumentPartProcessTestCase
from .export import DocumentExportTestCase
from .tasks import TasksTestCase 

__all__ = [
    DocumentTestCase,
    DocumentShareTestCase,
    DocumentExportTestCase,
    DocumentPartProcessTestCase,
    TasksTestCase
]
