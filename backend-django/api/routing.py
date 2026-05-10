from django.urls import re_path
from . import consumers


websocket_urlpatterns = [
    re_path(r"^api/ws/history$", consumers.HistoryConsumer.as_asgi()),
    re_path(r"^api/ws/tasks/(?P<task_id>[0-9a-f-]{36})$", consumers.TaskConsumer.as_asgi()),
]

