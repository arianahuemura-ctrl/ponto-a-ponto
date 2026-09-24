from django.test import TestCase
from django.conf import settings
from .importing import import_demo


class DemoDatabaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        import_demo(settings.BASE_DIR)
