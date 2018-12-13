var msgSocket;

$(document).ready(function() {
    msgSocket = new ReconnectingWebSocket('ws://' + window.location.host + '/ws/notif/');
    msgSocket.maxReconnectAttempts = 3;
    
    msgSocket.addEventListener('open', function(e) {
        console.log('Connected to notification socket');
    });
    
    msgSocket.addEventListener('message', function(e) {
        var data = JSON.parse(e.data);
        var $container = $('#alerts-container');
        
        if (DEBUG) {
            console.log('Received ws message: ', data);
        }

        if (data.type == 'notification_message') {
            var message = data['text'];
            // TODO: not dry
            alert = '<div class="alert alert-' + data["level"] + ' alert-dismissible fade show" role="alert">' + message + '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>';
            $container.append(alert);
        } else if (data.type == 'event') {
            $container.trigger(data["name"], data["data"]);
        }
    });
    
    msgSocket.addEventListener('close', function(e) {
        console.error('Notification socket closed unexpectedly');
    });
});
