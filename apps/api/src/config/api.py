from django.shortcuts import get_object_or_404
from ninja import ModelSchema, NinjaAPI

from catalog.models import Product

api = NinjaAPI()


class ProductOut(ModelSchema):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "description"]


@api.get("/health")
def health(request):
    return {"status": "ok"}


@api.get("/products", response=list[ProductOut])
def list_products(request):
    return Product.objects.order_by("id")


@api.get("/products/{product_id}", response=ProductOut)
def get_product(request, product_id: int):
    return get_object_or_404(Product, id=product_id)
