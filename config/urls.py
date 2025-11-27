import os

os.environ['GDAL_LIBRARY_PATH'] = r"C:\OSGeo4W\bin\gdal311.dll"
os.environ['PROJ_LIB'] = r"C:\OSGeo4W\share\proj"

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("rutas.urls")),
]
