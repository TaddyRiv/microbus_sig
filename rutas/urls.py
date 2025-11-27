from django.urls import path, include
from rest_framework import routers
from .views import (
    RutaViewSet,
    PuntoViewSet,
    LineaRutaViewSet,
    ruta_optima_coords,
    ruta_optima_ids,
    ruta_por_linea,
    rutas_todas
)

router = routers.DefaultRouter()
router.register(r'rutas', RutaViewSet)
router.register(r'puntos', PuntoViewSet)
router.register(r'lineas', LineaRutaViewSet)

urlpatterns = [

    # 🔵 RUTAS PERSONALIZADAS (PRIMERO)
    path("ruta-optima/", ruta_optima_coords, name="ruta_optima_coords"),
    path("rutas/optima/", ruta_optima_ids, name="ruta_optima_ids"),
    path("rutas/optima-coords/", ruta_optima_coords, name="ruta_optima_coords"),
    path("rutas/todas/", rutas_todas, name="todas_las_rutas"),
    path("rutas/linea/<str:linea>/", ruta_por_linea, name="ruta_por_linea"),

    # 🔵 Router DRF (AL FINAL SIEMPRE)
    path("", include(router.urls)),
]
