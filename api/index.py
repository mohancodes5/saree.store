"""
Vercel serverless entrypoint — exposes WSGI app as `app`.
"""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
