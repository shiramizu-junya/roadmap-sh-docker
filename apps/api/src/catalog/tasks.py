from django.core.files.base import ContentFile
from PIL import Image

from catalog.models import Product
from config.celery import app


@app.task
def make_thumbnail(product_id):
    product = Product.objects.get(id=product_id)
    img = Image.open(product.image)
    img.thumbnail((200, 200))
    thumb = ContentFile(b"")
    img.save(thumb, format="JPEG")
    product.thumbnail.save(f"{product_id}.jpg", thumb)
    return f"商品 {product_id} の画像は {img.size}"
