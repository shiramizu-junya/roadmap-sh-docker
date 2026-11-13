import redis
from django.conf import settings
from django.shortcuts import get_object_or_404
from ninja import Header, ModelSchema, NinjaAPI, Schema

from catalog.models import Product

api = NinjaAPI()
cart_store = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


class ProductOut(ModelSchema):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "description"]


class CartItemIn(Schema):
    product_id: int
    quantity: int = 1


@api.get("/health")
def health(request):
    return {"status": "ok"}


@api.get("/products", response=list[ProductOut])
def list_products(request):
    return Product.objects.order_by("id")


@api.get("/products/{product_id}", response=ProductOut)
def get_product(request, product_id: int):
    return get_object_or_404(Product, id=product_id)


@api.get("/cart")
def get_cart(request, cart_id: str = Header(alias="X-Cart-Id")):
    items = cart_store.hgetall(f"cart:{cart_id}")
    return {"items": {int(k): int(v) for k, v in items.items()}}


@api.post("/cart/items")
def add_cart_item(request, item: CartItemIn, cart_id: str = Header(alias="X-Cart-Id")):
    get_object_or_404(Product, id=item.product_id)
    cart_store.hincrby(f"cart:{cart_id}", item.product_id, item.quantity)
    return get_cart(request, cart_id)
