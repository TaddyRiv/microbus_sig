from django.contrib.gis.db import models

class Punto(models.Model):
    descripcion = models.CharField(max_length=255)
    ubicacion = models.PointField(geography=True)

    def __str__(self):
        return self.descripcion


class Ruta(models.Model):
    nombre = models.CharField(max_length=120)
    linea = models.CharField(max_length=50)
    color = models.CharField(max_length=10)

    def __str__(self):
        return self.nombre


class LineaRuta(models.Model):
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name='segmentos')
    geom = models.LineStringField(geography=True)

    def __str__(self):
        return f"Segmento de {self.ruta.nombre}"
    
class Edge(models.Model):
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE,null=True, blank=True)
    source = models.ForeignKey(Punto, related_name="edges_from", on_delete=models.CASCADE)
    target = models.ForeignKey(Punto, related_name="edges_to", on_delete=models.CASCADE)
    cost = models.FloatField()  # distancia o tiempo
    geom = models.LineStringField(geography=True)

    def __str__(self):
        return f"Edge from {self.source} to {self.target} on {self.ruta.nombre}"