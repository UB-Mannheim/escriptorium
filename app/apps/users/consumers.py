import json
import logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def get_group_name(user_pk):
    return 'notif-' + str(user_pk)


def get_room_name(cls, pk):
    return "room-%s-%d" % (cls, pk)


def can_join_room(user, cls, pk):
    """Joining a room is a read on the object it broadcasts, so it is
    checked like one. Only 'document' and 'collection' rooms are emitted to."""
    from core.models import Document, VirtualCollection

    try:
        pk = int(pk)
    except (TypeError, ValueError):
        return False

    if cls == 'document':
        return Document.objects.for_user(user).filter(pk=pk).exists()
    elif cls == 'collection':
        return VirtualCollection.objects.filter(pk=pk, owner=user).exists()
    return False


def send_event(cls, pk, event_name, data):
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            get_room_name(cls, pk),
            {'type': 'notification_event',
             'name': event_name,
             'data': data})
    except Exception as e:
        # channel fails shouldn't crash the calling process
        logger.exception(e)


def send_notification(user_pk, message, id=None, level='info', links=None):
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            get_group_name(user_pk),
            {'type': 'notification_message',
             'id': id,
             'level': level,
             'text': message,
             'links': links or []})
    except Exception as e:
        # channel fails shouldn't crash the calling process
        logger.exception(e)


class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        self.room = None
        self.rooms = set()
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
            for room in self.rooms:
                async_to_sync(self.channel_layer.group_discard)(
                    room,
                    self.channel_name)

    def receive(self, text_data):
        msg = json.loads(text_data)
        if 'type' in msg:
            if msg['type'] == 'notif' and self.scope['user'].is_superuser:  # DEBUG notifs
                send_notification(msg['user_pk'], msg['text'], level=getattr(msg, 'level', 'info'))
            elif msg['type'] == 'join-room':
                cls, pk = msg.get('object_cls'), msg.get('object_pk')
                if not can_join_room(self.scope['user'], cls, pk):
                    logger.warning(
                        "user %s denied join-room %s-%s",
                        self.scope['user'].pk, cls, pk)
                    return
                self.room = get_room_name(cls, pk)
                self.rooms.add(self.room)
                async_to_sync(self.channel_layer.group_add)(
                    self.room,
                    self.channel_name)

    def notification_message(self, event):
        self.send(json.dumps({'type': 'message',
                              'id': event['id'],
                              'level': event['level'],
                              'text': event['text'],
                              'links': event['links']}))

    def notification_event(self, event):
        self.send(json.dumps({'type': 'event',
                              'name': event['name'],
                              'data': event['data']}))
