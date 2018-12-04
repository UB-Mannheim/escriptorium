from django.test import TestCase



class DocumentListTestCase(TestCase):
    
    def test_list(self):
        with self.assertNumQueries(5):
            pass
