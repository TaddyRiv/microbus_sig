from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Punto, Ruta, LineaRuta

class PuntoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Punto
        geo_field = "ubicacion"
        fields = ("id", "descripcion")


class LineaRutaSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = LineaRuta
        geo_field = "geom"
        fields = ("id", "ruta")


class RutaSerializer(GeoFeatureModelSerializer):
    segmentos = LineaRutaSerializer(many=True, read_only=True)

    class Meta:
        model = Ruta
        geo_field = None
        fields = ("id", "nombre", "linea", "color", "segmentos")
