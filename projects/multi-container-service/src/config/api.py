from ninja import ModelSchema, NinjaAPI, Schema

from todos.models import Todo

api = NinjaAPI()


class TodoIn(Schema):
    title: str
    completed: bool = False


class TodoOut(ModelSchema):
    class Meta:
        model = Todo
        fields = ["id", "title", "completed"]


# 作る
@api.post("/todos", response={201: TodoOut})
def create_todo(request, data: TodoIn):
    return 201, Todo.objects.create(**data.dict())


# 一覧で見る
@api.get("/todos", response=list[TodoOut])
def list_todos(request):
    return Todo.objects.order_by("id")
