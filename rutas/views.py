from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import JsonResponse
from django.db import connection
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance

from .models import Punto, Ruta, LineaRuta, Edge
from .serializers import PuntoSerializer, RutaSerializer, LineaRutaSerializer

class PuntoViewSet(viewsets.ModelViewSet):
    queryset = Punto.objects.all()
    serializer_class = PuntoSerializer


class RutaViewSet(viewsets.ModelViewSet):
    queryset = Ruta.objects.all()
    serializer_class = RutaSerializer


class LineaRutaViewSet(viewsets.ModelViewSet):
    queryset = LineaRuta.objects.all()
    serializer_class = LineaRutaSerializer

@api_view(["GET"])
def ruta_por_linea(request, linea):
    try:
        ruta = Ruta.objects.get(linea=linea)
    except Ruta.DoesNotExist:
        try:
            ruta = Ruta.objects.get(nombre=linea)
        except:
            return Response({"error": "Línea no encontrada"}, status=404)

    segmentos = Edge.objects.filter(ruta=ruta)

    return Response({
        "ruta_id": ruta.id,
        "nombre": ruta.nombre.strip(),
        "linea": ruta.linea.strip(),
        "color": ruta.color.strip(),
        "segmentos": [
            {"id": s.id, "geometry": s.geom.geojson}
            for s in segmentos
        ]
    })

@api_view(["GET"])
def rutas_todas(request):
    data = []

    for r in Ruta.objects.all():
        segmentos = Edge.objects.filter(ruta=r)
        data.append({
            "ruta_id": r.id,
            "nombre": r.nombre.strip(),
            "linea": r.linea.strip(),
            "color": r.color.strip(),
            "segmentos": [
                {"id": s.id, "geometry": s.geom.geojson}
                for s in segmentos
            ]
        })

    return Response(data)


@api_view(["GET"])
def ruta_optima_coords(request):
    """Encuentra ruta óptima desde coordenadas (lat,lon)"""

    try:
        lat_origen = float(request.GET.get("lat_origen"))
        lon_origen = float(request.GET.get("lon_origen"))
        lat_destino = float(request.GET.get("lat_destino"))
        lon_destino = float(request.GET.get("lon_destino"))
    except:
        return Response({"error": "Parámetros inválidos"}, status=400)

    origen_geom = Point(lon_origen, lat_origen, srid=4326)
    destino_geom = Point(lon_destino, lat_destino, srid=4326)

    origen = Punto.objects.annotate(dist=Distance("ubicacion", origen_geom)).order_by("dist").first()
    destino = Punto.objects.annotate(dist=Distance("ubicacion", destino_geom)).order_by("dist").first()

    if not origen or not destino:
        return Response({"error": "No se encontraron puntos cercanos"}, status=404)

    return ejecutar_dijkstra(origen.id, destino.id)

@api_view(["GET"])
def ruta_optima_ids(request):
    """Encuentra ruta óptima desde IDs de puntos"""

    try:
        origen = int(request.GET.get("origen"))
        destino = int(request.GET.get("destino"))
    except:
        return JsonResponse({"error": "Debe enviar origen y destino"}, status=400)

    return ejecutar_dijkstra(origen, destino)

def ejecutar_dijkstra(origen, destino):
    sql = f"""
        SELECT * FROM pgr_dijkstra(
            'SELECT id, source_id AS source, target_id AS target, cost FROM rutas_edge',
            {origen},
            {destino},
            directed := true
        );
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        steps = cursor.fetchall()

    if not steps:
        return JsonResponse({"error": "No existe una ruta entre los puntos"}, status=404)

    # Lista de edges utilizados
    edge_ids = [row[3] for row in steps if row[3] != -1]

    features = []
    for edge_id in edge_ids:
        try:
            e = Edge.objects.get(id=edge_id)
        except Edge.DoesNotExist:
            continue

        features.append({
            "type": "Feature",
            "geometry": e.geom.geojson,
            "properties": {
                "edge": e.id,
                "ruta": e.ruta.linea if e.ruta else None
            }
        })

    return JsonResponse({
        "origen": origen,
        "destino": destino,
        "edges": edge_ids,
        "geojson": features
    })
