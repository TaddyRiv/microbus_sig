from django.core.management.base import BaseCommand
from django.contrib.gis.geos import LineString
from django.contrib.gis.db.models.functions import Distance
from rutas.models import Punto, Edge, Ruta
from django.db.models import F
from django.db import transaction

# Distancia máxima para transbordo caminando (en metros)
MAX_DIST = 20  # puedes subirlo a 30 si quieres

# Velocidad caminando (metros/minuto)
WALK_SPEED = 80


class Command(BaseCommand):
    help = "Genera transbordos entre líneas (exactos y por cercanía)"

    def handle(self, *args, **kwargs):
        self.stdout.write("🔄 Eliminando transbordos previos...")
        
        # Borrar todos los edges que sean transbordos:
        Edge.objects.filter(source_id=F('target_id')).delete()

        self.stdout.write("🚏 Generando transbordos exactos (mismo IdPunto)...")

        puntos = Punto.objects.all()

        total_exactos = 0
        with transaction.atomic():
            for punto in puntos:
                # Rutas distintas en el mismo punto
                edges = Edge.objects.filter(source=punto)

                rutas_distintas = Ruta.objects.filter(
                    id__in=edges.values_list('ruta', flat=True)
                ).distinct()

                if rutas_distintas.count() > 1:
                    # Transbordo directo dentro del mismo punto
                    for ruta in rutas_distintas:
                        for ruta2 in rutas_distintas:
                            if ruta != ruta2:
                                Edge.objects.create(
                                    ruta=ruta2,
                                    source=punto,
                                    target=punto,
                                    cost=0.1,  # costo mínimo por cambio de micro
                                    geom=LineString(
                                        (punto.ubicacion.x, punto.ubicacion.y),
                                        (punto.ubicacion.x, punto.ubicacion.y),
                                        srid=4326
                                    )
                                )
                                total_exactos += 1

        self.stdout.write(self.style.SUCCESS(f"✔️ {total_exactos} transbordos exactos generados"))

        self.stdout.write("🚶 Generando transbordos por cercanía (< 20 m)...")

        puntos = list(Punto.objects.all())
        total_cercania = 0

        with transaction.atomic():
            for i, p1 in enumerate(puntos):
                for p2 in puntos[i+1:]:
                    distancia = p1.ubicacion.distance(p2.ubicacion) * 111139  # grados → metros

                    if distancia <= MAX_DIST:
                        cost = distancia / WALK_SPEED  # minutos
                        
                        # Crear transbordo bidireccional
                        Edge.objects.create(
                            ruta=None,
                            source=p1,
                            target=p2,
                            cost=cost,
                            geom=LineString(
                                (p1.ubicacion.x, p1.ubicacion.y),
                                (p2.ubicacion.x, p2.ubicacion.y),
                                srid=4326
                            )
                        )
                        Edge.objects.create(
                            ruta=None,
                            source=p2,
                            target=p1,
                            cost=cost,
                            geom=LineString(
                                (p2.ubicacion.x, p2.ubicacion.y),
                                (p1.ubicacion.x, p1.ubicacion.y),
                                srid=4326
                            )
                        )
                        total_cercania += 2

        self.stdout.write(self.style.SUCCESS(f"✔️ {total_cercania} transbordos de cercanía generados"))
        self.stdout.write(self.style.SUCCESS("🎉 Todos los transbordos generados correctamente"))
