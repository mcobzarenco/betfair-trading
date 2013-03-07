
var IMAGES_ROOT = '/static/libs/DataTables-1.9.4/media/images/';
var events_table = null;

function zip(xs, ys) {
    var zipped = [];
    for (var i = 0; i < xs.length; i++) {
        zipped.push([xs[i], ys[i]]);
    }
    return zipped;
}


function describe_series(obj, title, fmt_value) {
    if(typeof(fmt_value)==='undefined')
        fmt_value = function(x) {return x;}
    var keys = Object.keys(obj);
    var $table = $('<table></table>').addClass('series');
    var $head = $('<thead></thead>').append($('<th></th>').attr('colspan', '2').html(title));
    var $body = $('<tbody></tbody>');
    for(var i in keys) {
        $body.append($('<tr></tr>')
            .append($('<td></td>').addClass('series_key').html(keys[i]))
            .append($('<td></td>').addClass('series_value').html(fmt_value(obj[keys[i]]))));
    }
    return $table.append($head).append($body);
}


function describe_table(objs, title, fmt_value) {
    if(typeof(fmt_value)==='undefined')
        fmt_value = function(x) {return x;}
    var cols = Object.keys(objs);
    var keys = Object.keys(objs[cols[0]]);
    var $table = $('<table></table>').addClass('series');
    var $head = $('<thead></thead>');
    var $body = $('<tbody></tbody>');

    $head.append($('<tr></tr>').append($('<th></th>').attr('colspan', cols.length + 1).html(title)));
    $head.append($('<tr></tr>').append($('<th></th>')).append(cols.map(
        function(x) {
            return $('<th></th>').addClass('series_subheader').html(x);
        }
    )));

    for(var k in keys) {
        var $tr = $('<tr></tr>');
        $tr.append($('<td></td>').addClass('series_key').html(keys[k]));
        for(var c in cols)
                $tr.append($('<td></td>').addClass('series_value').html(fmt_value(objs[cols[c]][keys[k]])))
        $body.append($tr);
    }
    return $table.append($head).append($body);
}

function toFixed2(x) {
    return x.toFixed(2);
}


function open_row(row, bets) {
    if(bets.length == 0)
        return;

    var dist_id = 'dist_' + bets[0]['event_id'];
    var $details = $('<div></div>');
    var $distribution = $('<div></div>').attr('id', dist_id);
    var $table = $('<table></table>').css('width', '100%');
    $details.append($('<div></div>').addClass('row-fluid').append($('<div></div>').addClass('span8').append($table)))
            .append($('<div></div>').addClass('row-fluid').append($('<div></div>').addClass('span12').append($distribution)));
    events_table.fnOpen(row, $details, 'details');

    $table.dataTable({
        aaData: bets,
        sDom: '<"top">rt<"bottom"flp><"clear">',
        aoColumns: [
            {
                'sTitle': 'Selection',
                'mData': 'selection'
            },
            {
                'sTitle': 'Amount',
                'sClass': 'series_value',
                'mData': function(source) {return source['amount'].toFixed(2);}
            },

            {
                'sTitle': 'Matched Odds',
                'sClass': 'series_value',
                'mData': function(source) {return source['odds'].toFixed(2);}
            },
            {
                'sTitle': 'Model Odds',
                'sClass': 'series_value',
                'mData': function(source) {return source['u_odds'].toFixed(2);}
            },
            {
                'sTitle': 'Volume Matched',
                'sClass': 'series_value',
                'mData': function(source) {return source['volume_matched'].toFixed(2);}
            },
            {
                'sTitle': 'Won',
                'sClass': 'series_value',
                'mData': 'selection_won'
            },
            {
                'sTitle': 'PnL',
                'sClass': 'series_value',
                'mData': function(source) {return source['pnl'].toFixed(2);}
            }
        ],
        bPaginate: false,
        bFilter: false
    });


    var runners = bets.map(function(b) {return b['selection']});
    new Highcharts.Chart({
        chart: {
            renderTo: dist_id,
            backgroundColor: '#E8E8E8',
            type: 'column',
            height: 440
        },
        credits: {
            enabled: false
        },
        title: {
            text: 'Daily PnL',
            x: -20 //center
        },
        xAxis:{
            categories: runners,
            labels: {
                align:'left'
            }
        },
        yAxis: {
            title: {
                text: 'Cummulative PnL (GBP)'
            },
            plotLines: [
                {
                    value: 0,
                    width: 1,
                    color: '#808080'
                }
            ]
        },
        tooltip: {
            valueDecimals:2
        },
        plotOptions:{
            line: {
                marker:{
                    enabled:false
                }
            },
            column: {
                borderWidth: 0.1,
                groupPadding: 0.04,
                pointPadding: 0,
                shadow: true
            }
        },
        series: [
            {
                name: 'Odds',
                data: zip(runners, bets.map(function(b) {return b['odds']}))
            },
            {
                name: 'Model',
                data: zip(runners, bets.map(function(b) {return b['u_odds']}))
            }
        ]
    });
}

function attach_accordion_handlers() {
    $('#events_table td.control').off('click');
    $('#events_table td.control').on('click', function () {
        var parent = this.parentNode;

        if(!$(parent).hasClass('accordion-open')) {
            $('img', this).attr('src', IMAGES_ROOT + "details_close.png");
            var row_data = events_table.fnGetData(parent);
            $.ajax({
                'url': '/api/bets/' + scorecard['scorecard_id'] + '/' + row_data['event_id'],
                'success': function(bets) {open_row(parent, bets);}
            });
        }
        else {
            $('img', this).attr('src', IMAGES_ROOT + "details_open.png");
            events_table.fnClose(parent);
        }
        $(parent).toggleClass('accordion-open');
    } );
}


$(function() {
    $('#scorecard_id').html(scorecard['scorecard_id']);

    $('#timestamp').html(scorecard['timestamp']);
    $('#time_taken').html(scorecard['run_seconds'].toFixed(0));

    var llik_series = describe_series(scorecard['llik'], 'Likelihood', toFixed2);
    var params_ts_series = describe_series(scorecard['params']['ts'], 'Trueskill', toFixed2);
    var params_risk__series = describe_series(scorecard['params']['risk'], 'Risk', toFixed2);

    var events_series = describe_table(scorecard['events'], 'Events', toFixed2);
    var all_series = describe_table(scorecard['all'], 'Bets', toFixed2);
    var backs_series = describe_table(scorecard['backs'], 'Bets (backs)', toFixed2);
    var lays_series = describe_table(scorecard['lays'], 'Bets (lays)', toFixed2);

    $('#llik_series').append(llik_series);
    $('#params_ts').append(params_ts_series);
    $('#params_risk').append(params_risk__series);
    $('#events_series').append(events_series);
    $('#all_series').append(all_series);
    $('#backs_series').append(backs_series);
    $('#lays_series').append(lays_series);

    $('.series').addClass('table table-condensed');


    var dates = scorecard['daily_pnl'].map(function(x){ return Date.parse(x['scheduled_off']);});
    new Highcharts.StockChart({
        chart: {
            renderTo: 'daily_pnl',
            backgroundColor: '#E8E8E8',
            //type: 'column',
            zoomType: 'x',
            height: 440
        },
        credits:{
            enabled:false
        },
        title: {
            text: 'Daily PnL',
            x: -20 //center
        },
        xAxis:{
            type:'datetime',
            labels:{
                align:'left'
            }
        },
        yAxis: {
            title: {
                text: 'Cummulative PnL (GBP)'
            },
            plotLines: [
                {
                    value: 0,
                    width: 1,
                    color: '#808080'
                }
            ]
        },
        tooltip: {
            valueDecimals:2
        },
        plotOptions:{
            line: {
                marker:{
                    enabled:false
                }
            },
            column: {
                borderWidth: 0.1,
                groupPadding: 0,
                pointPadding: 0,
                shadow: false
            }
        },
        series: [
            {
                type: 'column',
                name: 'Daily Net',
                color: 'grey',
                data: zip(dates, scorecard['daily_pnl'].map(function(x) {return x['net']}))
            },
            {
                type: 'line',
                name: 'Cumm. Gross.',
                data: zip(dates, scorecard['daily_pnl'].map(function(x) {return x['gross_cumm']}))
            },
            {
                type: 'line',
                name: 'Cumm. Net',
                data: zip(dates, scorecard['daily_pnl'].map(function(x) {return x['net_cumm']}))
            }
        ]
    });

    events_table = $('#events_table').dataTable({
        'sDom': "<'row-fluid'<'span6'l><'span6'f>r>t<'row-fluid'<'span6'i><'span6'p>>",
        'bProcessing': true,
        'sAjaxSource': '/api/events/' + scorecard['scorecard_id'],
        'sAjaxDataProp': '',
        'aoColumns': [
            {
                'mData':null,
                'sClass':'control centre',
                'sDefaultContent':'<img src="' + IMAGES_ROOT + 'details_open.png">',
                'sTitle':''
            },
            {
                'sTitle': 'Scheduled Off (UTC)',
                'mData': function(source, type, val) {
                    if(typeof type === 'undefined') {
                        source.timestamp = moment(source['scheduled_off']);
                    }

                    if (type === 'display' || type === 'filter') {
                        return  source.timestamp.format("YYYY-MM-DD HH:mm");
                    }
                    return source.timestamp;
                }
            },
            {
                'sTitle': 'Event ID',
                'mData': 'event_id'
            },
            {
                'sTitle': 'Event',
                'mData': 'event'
            },
            {
                'sTitle': 'Course',
                'mData': 'course'
            },
            {
                'sTitle': 'Collateral',
                'mData': function(source) {return source['coll'].toFixed(2);},
                'sClass': 'series_value'
            },
            {
                'sTitle': 'PnL (Gross)',
                'mData': function(source) {return source['pnl_gross'].toFixed(2);},
                'sClass': 'series_value'
            },
            {
                'sTitle': 'PnL (Net)',
                'mData': function(source) {return source['pnl_net'].toFixed(2);},
                'sClass': 'series_value'
            }
        ],
        'bAutoWidth':false,
        'sPaginationType':'bootstrap',
        "iDisplayLength": 50,
        fnDrawCallback: attach_accordion_handlers
    });

});



