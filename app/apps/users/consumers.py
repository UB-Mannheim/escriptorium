import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer


def get_group_name(user_pk):
    return 'notif-' + str(user_pk)


def send_notification(user_pk, message, level='info'):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        get_group_name(user_pk),
        {'type': 'notification_message',
         'level': level,
         'text': message},
    )


class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        if self.scope['user'].is_authenticated:
            async_to_sync(self.channel_layer.group_add)(
                get_group_name(self.scope['user'].pk),
                self.channel_name)
            self.accept()
        
    def disconnect(self, close_code):
        if self.scope['user'].is_authenticated:
            async_to_sync(self.channel_layer.group_discard)(
                get_group_name(self.scope['user'].pk),
                self.channel_name)
            self.close()
        
    def receive(self, text_data):
        data = json.loads(text_data)
        send_notification(data['user_pk'], data['text'], level=data['level'])
    
    def notification_message(self, event):
        self.send(json.dumps({'level': event['level'], 'text': event['text']}))
