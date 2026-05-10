from channels.generic.websocket import AsyncWebsocketConsumer


class JsonTextConsumer(AsyncWebsocketConsumer):
    group_name: str | None = None

    async def connect(self):
        if not self.group_name:
            await self.close(code=1008)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def task_message(self, event):
        await self.send(text_data=event.get("text", ""))


class HistoryConsumer(JsonTextConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_name = "history"


class TaskConsumer(JsonTextConsumer):
    async def connect(self):
        self.group_name = f"task-{self.scope['url_route']['kwargs']['task_id']}"
        await super().connect()

