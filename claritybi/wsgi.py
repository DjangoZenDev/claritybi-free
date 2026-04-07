"""WSGI config for claritybi project."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "claritybi.settings")
application = get_wsgi_application()
