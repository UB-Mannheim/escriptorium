var msgSocket;

var alerts = {};
class Alert {
    constructor(id, message, level, url) {
        this.id = id;
        this.count = 1;
        this.message = message;
        this.level = level || 'info';
        this.url = url;

        var $new = $('.alert', '#alert-tplt').clone();
        $new.addClass('alert-' + this.level);
        $('.message', $new).html(message);
        if (this.url) {
            $('.additional', $new).html('<a href="'+this.url+'" />').show();
            $('.separator', $new).show();
        }
        this.$element = $new;
        $('#alerts-container').append($new);
        $new.show();

        this.$element.on('closed.bs.alert', $.proxy(function () {
            delete alerts[this.id];
        }, this));
    }

    static add(id, message, url) {
        var id_ = id || new Date().getTime();
        if (alerts[id_] === undefined) {
            alerts[id_] = new Alert(id_, message, url);
        } else {
            alerts[id_].incrementCounter();
        }
    }

    incrementCounter() {
        this.count++;
        $('.counter', this.$element).text('('+this.count+')').show();
    }
}

$(document).ready(function() {
    msgSocket = new ReconnectingWebSocket('ws://' + window.location.host + '/ws/notif/');
    msgSocket.maxReconnectAttempts = 3;
    
    msgSocket.addEventListener('open', function(e) {
        if (DEBUG) {
            console.log('Connected to notification socket');
        }
    });
    
    msgSocket.addEventListener('message', function(e) {
        var data = JSON.parse(e.data);

        if (DEBUG) {
            console.log('Received ws message: ', data);
        }

        if (data.type == 'message') {
            var message = data['text'];
            Alert.add(data['id'], message);
        } else if (data.type == 'event') {
            var $container = $('#alerts-container');
            $container.trigger(data["name"], data["data"]);
        }
    });
    
    msgSocket.addEventListener('close', function(e) {
        if (DEBUG) {
            console.error('Notification socket closed unexpectedly');
        }
    });
});
