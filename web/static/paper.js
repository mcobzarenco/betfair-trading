
$(function() {
    $('#strats_table').dataTable({
        'sDom': "<'row-fluid'<'span6'l><'span6'f>r>t<'row-fluid'<'span6'i><'span6'p>>",
        'bProcessing': true,
        'aaData': strats,
        'sAjaxDataProp': '',
        'aoColumns': [
            {
                'sTitle': 'Strategy ID',
                'mData': function(source, type, val) {
                    if (type === 'set') {
                        source.id_link = '<a href="paper/detail/' + source.strategy_id + '">' + source.strategy_id + '</a>';
                        return source._id;
                    }
                    else if (type === 'display') {
                        return source.id_link;
                    }
                    else if (type === 'filter') {
                        return source.strategy_id;
                    }
                    // 'sort', 'type' and undefined all just use the integer
                    return source.strategy_id;
                }
            }
        ],
        'bAutoWidth':false,
        'sPaginationType':'bootstrap',
        "iDisplayLength": 50
    });
});
