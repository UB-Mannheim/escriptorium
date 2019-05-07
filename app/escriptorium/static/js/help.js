$(document).ready(function() {
    let closed = userProfile.get('closedHelps');
    
    $('.help-text .close').click(function(ev) {
        let btn = $(ev.target);
        let container = btn.parents('.js-help-container');
        if (!closed) closed = [];
        if (container.attr('id')) {
            closed.push(container.attr('id'));
            userProfile.set('closedHelps', closed);
        }
        $('.alert.help-text', container).hide();
        $('button.help.open', container).show();
    });

    $('button.help.open').click(function(ev) {
        let btn = $(ev.target);
        let container = btn.parents('.js-help-container');
        let helpIndex = closed.indexOf(container.attr('id'));
        if (helpIndex != -1) closed.splice(helpIndex, 1);
        userProfile.set('closedHelps', closed);
        
        $('.alert.help-text', container).show();
        $('button.help.open', container).hide();
    });
    
    if (closed) {
        closed.forEach(function(e, i) {
            let container = $('.js-help-container#'+e);
            $('.alert.help-text', container).hide();
            $('button.help.open', container).show();
        });
    }
});
