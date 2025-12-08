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

from heapq import heappush, heappop
import json
from math import radians, cos, sin, sqrt, atan2
from collections import defaultdict

import itertools
counter = itertools.count()

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


TRANSFER_RADIUS_METERS = 25  # radio máximo para considerar un transbordo
TRANSFER_COST = 0.0          # costo de "caminar" entre paradas cercanas


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000  # radio de la Tierra en metros
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def punto_mas_cercano(lat, lon):
    p = Point(lon, lat, srid=4326)
    return Punto.objects.annotate(
        distancia=Distance("ubicacion", p)
    ).order_by("distancia").first()


def construir_grafo_con_transbordos():

    graph = defaultdict(list)

    #Edges de la BD (movimiento en microbus)
    for e in Edge.objects.all():
        # Edge dirigido
        graph[e.source_id].append((e.target_id, e.cost, e.ruta_id, "bus"))
        # Si quieres que sea bidireccional, descomenta:
        # graph[e.target_id].append((e.source_id, e.cost, e.ruta_id, "bus"))

    #Edges de transbordo entre puntos cercanos (a pie)
    puntos = list(Punto.objects.all())
    coords = {p.id: (p.ubicacion.y, p.ubicacion.x) for p in puntos}  # id -> (lat, lon)
    ids = [p.id for p in puntos]

    for i in range(len(ids)):
        id_a = ids[i]
        lat_a, lon_a = coords[id_a]
        for j in range(i+1, len(ids)):
            id_b = ids[j]
            lat_b, lon_b = coords[id_b]
            d = haversine_m(lat_a, lon_a, lat_b, lon_b)
            if d <= TRANSFER_RADIUS_METERS:
                # Edge de "caminar" entre paradas (bidireccional)
                graph[id_a].append((id_b, TRANSFER_COST, None, "transfer"))
                graph[id_b].append((id_a, TRANSFER_COST, None, "transfer"))

    return graph

def dijkstra_con_transbordos(graph, origen_id, destino_id):
    """
    Devuelve: (costo_total, pasos)
    pasos = lista de dicts: {source, target, ruta_id, modo}
    """

    heap = []
    heappush(heap, (0.0, next(counter), origen_id, []))  # (costo, orden, nodo, pasos)
    mejor_costo = {}

    while heap:
        costo, _, nodo, pasos = heappop(heap)

        if nodo in mejor_costo and mejor_costo[nodo] <= costo:
            continue
        mejor_costo[nodo] = costo

        if nodo == destino_id:
            return costo, pasos

        for vecino, edge_cost, ruta_id, modo in graph.get(nodo, []):
            nuevo_costo = costo + edge_cost

            nuevo_pasos = pasos + [{
                "source": nodo,
                "target": vecino,
                "ruta_id": ruta_id,
                "modo": modo,
            }]

            heappush(
                heap,
                (nuevo_costo, next(counter), vecino, nuevo_pasos)
            )

    return None, []


@api_view(["GET"])
def ruta_optima(request):
    try:
        lat_origen = float(request.GET.get("lat_origen"))
        lon_origen = float(request.GET.get("lon_origen"))
        lat_destino = float(request.GET.get("lat_destino"))
        lon_destino = float(request.GET.get("lon_destino"))
    except (TypeError, ValueError):
        return Response({"error": "Parámetros lat/lon inválidos"}, status=400)

    # Buscar puntos cercanos
    p_origen = punto_mas_cercano(lat_origen, lon_origen)
    p_destino = punto_mas_cercano(lat_destino, lon_destino)

    if not p_origen or not p_destino:
        return Response({"error": "No se encontraron puntos cercanos"}, status=404)

    # Grafo completo
    graph = construir_grafo_con_transbordos()

    # Ejecutar Dijkstra con transbordos
    costo_total, pasos = dijkstra_con_transbordos(graph, p_origen.id, p_destino.id)

    if costo_total is None:
        return Response({"error": "No existe ruta entre origen y destino"}, status=404)


    resultado = []

    for paso in pasos:
        source_id = paso["source"]
        target_id = paso["target"]
        modo = paso["modo"]         # bus / transfer
        ruta_id = paso["ruta_id"] 

        # ---------- BUS ----------
        if modo == "bus":
            e = Edge.objects.filter(source_id=source_id, target_id=target_id).first()
            if not e:
                continue

            linea = e.ruta.linea if hasattr(e, "ruta") else f"L{ruta_id:03d}"

            # Color asignado segun línea
            color = obtener_color_hex(linea)

            resultado.append({
                "tipo": "bus",
                "linea": linea,
                "ruta_id": ruta_id,
                "color": color,
                "geometry": json.loads(e.geom.geojson)["coordinates"]
            })

        # ---------- TRANSFER ----------
        else:
            p1 = Punto.objects.get(id=source_id)
            p2 = Punto.objects.get(id=target_id)

            resultado.append({
                "tipo": "transfer",
                "descripcion": "Transferencia entre líneas",
                "geometry": [
                    [p1.ubicacion.x, p1.ubicacion.y],
                    [p2.ubicacion.x, p2.ubicacion.y],
                ]
            })

    return Response({
        "costo_total": costo_total,
        "ruta_optima": resultado
    })


def obtener_color_hex(linea):
    colores = {
        "L001": "#FF0000",
        "L002": "#0066FF",
        "L005": "#00AA00",
        "L008": "#FF9900",
        "L009": "#9933FF",
        "L010": "#FF5555",
        "L011": "#008B8B",
        "L016": "#000000",
        "L017": "#FF6600",
        "L018": "#0099FF",
    }
    return colores.get(linea, "#777777")  # gris por defecto
