
$(function() {
    $('#bets_table').dataTable({
        'sDom': "<'row-fluid'<'span6'l><'span6'f>r>t<'row-fluid'<'span6'i><'span6'p>>",
        'bProcessing': true,
        'aaData': bets,
        'sAjaxDataProp': '',
        'aoColumns': [
            {
                sTitle: 'Bet placed (UTC)',
                mData: function(source, type, val) {
                    if (type == 'display') {
                        return moment(source['timestamp']).fromNow();
                    }
                    return moment(source['timestamp']);
                }
            },
            {
                sTitle: 'Market ID',
                mData: function(source) {
                    return '<a href="http://www.betfair.com/exchange/horse-racing/market?id=1.' +
                        source.market_id + '" target="_blank">' + source. market_id +  '</a>';
                }
            },
            {
                sTitle: 'Event',
                mData: 'event'
            },
            {
                sTitle: 'Scheduled off (UTC)',
                mData: function(source, type, val) {
                    if (type == 'display') {
                        return moment(source['scheduled_off']).fromNow();
                    }
                    return moment(source['scheduled_off']);
                }
            },
            {
                sTitle: 'Selection',
                mData: 'selection'
            },
            {
                sTitle: 'Type',
                mData: function(source) {
                    if (source['amount'] < 0)
                        return 'Back'
                    else
                        return 'Lay'
                }
            },
            {
                sTitle: 'Amount',
                mData: function(source) {return source['amount'].toFixed(2);}
            },
            {
                sTitle: 'Odds',
                mData: 'odds'
            }
        ],
        'bAutoWidth':false,
        'sPaginationType':'bootstrap',
        "iDisplayLength": 50
    });
});
