var msgSocket;
$(document).ready(function() {
    msgSocket = new WebSocket('ws://' + window.location.host + '/ws/notif/');

    msgSocket.onopen = function(e) {
        console.log('Connected to notification socket');
    };
    
    msgSocket.onmessage = function(e) {
        var data = JSON.parse(e.data);
        var message = data['text'];
        console.log('Received notification: ' + message);

        $container = $('#alerts-container');
        // TODO: not dry
        alert = '<div class="alert alert-' + data["level"] + ' alert-dismissible fade show" role="alert">' + message + '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>';
        $container.append(alert);
    };
    
    msgSocket.onclose = function(e) {
        console.error('Notification socket closed unexpectedly');
    };
});
