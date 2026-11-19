from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True)
    thumbnail = models.ImageField(upload_to="thumbs/", blank=True)

    def __str__(self):
        return self.name
