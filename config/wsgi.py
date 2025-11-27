import os

os.environ['GDAL_LIBRARY_PATH'] = r"C:\OSGeo4W\bin\gdal311.dll"
os.environ['PROJ_LIB'] = r"C:\OSGeo4W\share\proj"

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
