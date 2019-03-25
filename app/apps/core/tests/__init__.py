from .views import DocumentListTestCase
from .share import DocumentShareTestCase
from .process import DocumentPartProcessTestCase
from .export import DocumentExportTestCase
from .tasks import TasksTestCase 

__all__ = [
    DocumentListTestCase,
    DocumentShareTestCase,
    DocumentExportTestCase,
    DocumentPartProcessTestCase,
    TasksTestCase
]
