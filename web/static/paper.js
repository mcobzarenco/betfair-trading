
$(function() {
    $('#strats_table').dataTable({
        'sDom': "<'row-fluid'<'span6'l><'span6'f>r>t<'row-fluid'<'span6'i><'span6'p>>",
        'bProcessing': true,
        'aaData': strats,
        'sAjaxDataProp': '',
        'aoColumns': [
            {
                sTitle: 'Strategy ID',
                mData: function(source) {
                    return source['strategy_id'] + ' [<a href="summary/' + source['strategy_id'] + '/bets">bets</a>]'
                },
                sClass: 'pre'
            },
            {
                sTitle: 'First Traded',
                mData: function(source, type, val) {
                    if (type == 'display') {
                        return moment(source['first_traded']).fromNow();
                    }
                    return moment(source['first_traded']);
                }
            },
            {
                sTitle: 'Last Traded',
                mData: function(source, type, val) {
                    if (source['last_traded'] == null)
                        return null
                    if (type == 'display')
                        return moment(source['last_traded']).fromNow();
                    return moment(source['last_traded']);
                }
            }
        ],
        'bAutoWidth':false,
        'sPaginationType':'bootstrap',
        "iDisplayLength": 50
    });
});
