import os
import sys

# --- ensure Passenger can find your Django project ---
sys.path.insert(0, '/home/deephubc/efe')
sys.path.insert(0, '/home/deephubc/efe/efe')

# --- set the Django settings module ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'efe.settings')

# --- get the application ---
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()