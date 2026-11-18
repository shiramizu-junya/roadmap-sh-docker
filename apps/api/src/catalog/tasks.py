from config.celery import app


@app.task
def make_thumbnail(product_id):
    return f"商品 {product_id} のメモを受け取った"
