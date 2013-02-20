
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

$(function() {
    $('.scorecard_id').html(scorecard['_id']);

    $('#timestamp').html(scorecard['timestamp']);
    $('#time_taken').html(scorecard['run_seconds'].toFixed(0));

    var llik_series = describe_series(scorecard['llik'], 'Likelihood', toFixed2);
    var params_ts_series = describe_series(scorecard['params']['ts'], 'Trueskill', toFixed2);
    var params_risk__series = describe_series(scorecard['params']['risk'], 'Risk', toFixed2);

    var events_series = describe_table(scorecard['events'], 'Events', toFixed2);
    var all_series = describe_table(scorecard['all'], 'All', toFixed2);
    var backs_series = describe_table(scorecard['backs'], 'Backs', toFixed2);
    var lays_series = describe_table(scorecard['lays'], 'Lays', toFixed2);

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
});



