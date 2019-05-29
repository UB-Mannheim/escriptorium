$(document).ready(function() {
    let $alertsContainer = $('#alerts-container');

    let max_accuracy = {};

    $('#models-table tr.model-head').each(function(i, e) {
        max_accuracy[$(e).data('id')] = $('td#accuracy-'+$(e).data('id'), e).data('value');
    });
    
    $alertsContainer.on('training:eval', function(ev, data) {
        let $row = $('tr#tr-'+data.id);
        if (max_accuracy[data.id] < data.accuracy) {
            $row.data('value', data.accuracy);
            $('td#accuracy-'+e.data('id'), $row).text(Math.round(data.accuracy*100, 1));
            max_accuracy[data.id] = data.accuracy;
        }
    });
});
