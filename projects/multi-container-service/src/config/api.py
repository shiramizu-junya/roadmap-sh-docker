from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/todos")
def hello(request):
    return {"message": "hello"}
