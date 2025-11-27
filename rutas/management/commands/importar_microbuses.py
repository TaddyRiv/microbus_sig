import pandas as pd
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point, LineString

from rutas.models import Punto, Ruta, LineaRuta, Edge


class Command(BaseCommand):
    help = "Importa datos del Excel (Puntos, Rutas, LineasPuntos) y genera los Edges"

    def add_arguments(self, parser):
        parser.add_argument('excel_path', type=str, help='Ruta al archivo Excel con los datos')

    def handle(self, *args, **options):
        excel_path = options['excel_path']
        self.stdout.write(self.style.SUCCESS(f"📄 Cargando datos desde: {excel_path}"))

        xls = pd.ExcelFile(excel_path, engine='openpyxl')

        puntos_df = pd.read_excel(xls, 'Puntos')

        self.stdout.write("📍 Importando Puntos...")
        Punto.objects.all().delete()

        for _, row in puntos_df.iterrows():
            Punto.objects.create(
                id=row['IdPunto'],  
                descripcion=row['Descripcion'],
                ubicacion=Point(float(row['Longitud']), float(row['Latitud']), srid=4326)
            )

        self.stdout.write(self.style.SUCCESS(f"✔️ {len(puntos_df)} Puntos importados"))

        lineas_df = pd.read_excel(xls, 'Lineas')

        self.stdout.write("🚌 Importando Rutas (Lineas)...")
        Ruta.objects.all().delete()

        for _, row in lineas_df.iterrows():
            Ruta.objects.create(
                id=row['IdLinea'],
                nombre=row['NombreLinea'],
                linea=row['NombreLinea'],  
                color=row['ColorLinea']
            )

        self.stdout.write(self.style.SUCCESS(f"✔️ {len(lineas_df)} Rutas importadas"))

        lineas_rutas_df = pd.read_excel(xls, 'LineaRuta')

        self.stdout.write("🔗 Importando LineaRuta...")
        LineaRuta.objects.all().delete()

        for _, row in lineas_rutas_df.iterrows():
            ruta = Ruta.objects.get(id=row['IdLinea'])
            LineaRuta.objects.create(
                id=row['IdLineaRuta'],
                ruta=ruta,
                geom=LineString()  
            )

        self.stdout.write(self.style.SUCCESS(f"✔️ {len(lineas_rutas_df)} LineaRuta importadas"))

        lineas_puntos_df = pd.read_excel(xls, 'LineasPuntos')

        self.stdout.write("🧩 Generando Edges para Dijkstra...")
        Edge.objects.all().delete()

        grupos = lineas_puntos_df.groupby('IdLineaRuta')

        total_edges = 0

        for id_linea_ruta, grupo in grupos:
            grupo = grupo.sort_values(by='Orden')

            # Obtener la Ruta real
            linea_ruta = LineaRuta.objects.get(id=id_linea_ruta)
            ruta = linea_ruta.ruta

            puntos = grupo[['IdPunto', 'Latitud', 'Longitud', 'Distancia', 'Tiempo']].values

            for i in range(len(puntos) - 1):
                p1 = puntos[i]
                p2 = puntos[i + 1]

                punto_source = Punto.objects.get(id=p1[0])
                punto_target = Punto.objects.get(id=p2[0])

                cost = float(p2[4])  

                geom = LineString(
                    (float(p1[2]), float(p1[1])),
                    (float(p2[2]), float(p2[1])),
                    srid=4326
                )

                Edge.objects.create(
                    ruta=ruta,
                    source=punto_source,
                    target=punto_target,
                    cost=cost,
                    geom=geom,
                )

                total_edges += 1

        self.stdout.write(self.style.SUCCESS(f" {total_edges} Edges generados con éxito"))
        self.stdout.write(self.style.SUCCESS(" Importación completa"))
