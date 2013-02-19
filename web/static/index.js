
function render_scorecard(card, a, b) {
    $('#card').html(card['lik']);
}

function render_bets(bets) {
    $('#bets_table').html(bets);
}

function scorecard_table(scorecard) {
    $('.dataframe').addClass('table');
}


function err(data, a, b) {
    var i = 0;
}


$(function() {
    $('#scorecards_table').dataTable({
        'bProcessing': true,
        'sAjaxSource': '/scorecards',
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
                'mData': 'mu'
            },
            {
                'sTitle': 'sigma',
                'mData': 'sigma'
            },
            {
                'sTitle': 'beta',
                'mData': 'beta'
            },
            {
                'sTitle': 'tau',
                'mData': 'tau'
            },
            {
                'sTitle': 'Mean PnL',
                'mData': function(source) {return source['mean_pnl'].toFixed(2);}
            },
            {
                'sTitle': 'log(model/implied)',
                'mData': function(source) {return source['diff_lik'].toFixed(2);}
            }
        ]
    });
});
