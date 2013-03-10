
$(function() {
    $('#bets_table').dataTable({
        'sDom': "<'row-fluid'<'span6'l><'span6'f>r>t<'row-fluid'<'span6'i><'span6'p>>",
        'bProcessing': true,
        'aaData': bets,
        'sAjaxDataProp': '',
        'aoColumns': [
            {
                sTitle: 'Market ID',
                mData: 'market_id'
            }
        ],
        'bAutoWidth':false,
        'sPaginationType':'bootstrap',
        "iDisplayLength": 50
    });
});
