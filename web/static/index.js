
function render_scorecard(card, a, b) {
    $('#card').html(card['lik']);
}

function render_bets(bets) {
    $('#bets_table').html(bets);
}

function scorecard_table(scorecard) {
    $('.dataframe').addClass('table');
}


function to(data, a, b) {
    var i = 0;
}


$(function() {
    $('#scorecards_table').dataTable({
        'sDom': "<'row-fluid'<'span6'l><'span6'f>r>t<'row-fluid'<'span6'i><'span6'p>>",
        'bProcessing': true,
        'aaData': scorecards,
        'sAjaxDataProp': '',
        'aoColumns': [
            {
                'sTitle': 'Timestamp',
                'mData': 'timestamp'
            },
            {
                'sTitle': 'ID',
                'mData': function(source, type, val) {
                    if (type === 'set') {
                        source.id_link = '<a href="detail/' + source._id + '">' + source._id + '</a>';
                        return source._id;
                    }
                    else if (type === 'display') {
                        return source.id_link;
                    }
                    else if (type === 'filter') {
                        return source._id;
                    }
                    // 'sort', 'type' and undefined all just use the integer
                    return source._id;
                }
            },
            {
                'sTitle': 'mu',
                'mData': function(source) {return source['mu'].toFixed(2);}
            },
            {
                'sTitle': 'sigma',
                'mData': function(source) {return source['sigma'].toFixed(2);}
            },
            {
                'sTitle': 'beta',
                'mData': function(source) {return source['beta'].toFixed(2);}
            },
            {
                'sTitle': 'tau',
                'mData': function(source) {return source['tau'].toFixed(2);}
            },
            {
                'sTitle': 'Mean PnL',
                'mData': function(source) {return source['mean_pnl'].toFixed(2);}
            },
            {
                'sTitle': 'llik(implied)',
                'mData': function(source) {return source['llik_implied'].toFixed(2);}
            },
            {
                'sTitle': 'llik(model)',
                'mData': function(source) {return source['llik_model'].toFixed(2);}
            },
            {
                'sTitle': 'diff',
                'mData': function(source) {return (source['diff'] * 100).toFixed(2);}
            }
        ],
        'bAutoWidth':false,
        'sPaginationType':'bootstrap',
        "iDisplayLength": 50
    });
});
