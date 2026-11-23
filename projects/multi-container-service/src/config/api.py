from django.shortcuts import get_object_or_404
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


# 1つ見る
@api.get("/todos/{todo_id}", response=TodoOut)
def get_todo(request, todo_id: int):
    return get_object_or_404(Todo, id=todo_id)


# 直す
@api.put("/todos/{todo_id}", response=TodoOut)  # ②
def update_todo(request, todo_id: int, data: TodoIn):  # ③
    todo = get_object_or_404(Todo, id=todo_id)
    todo.title = data.title
    todo.completed = data.completed  # ④
    todo.save()
    return todo


# 消す
@api.delete("/todos/{todo_id}", response={204: None})  # ⑤
def delete_todo(request, todo_id: int):
    todo = get_object_or_404(Todo, id=todo_id)
    todo.delete()
    return 204, None  # ⑥
