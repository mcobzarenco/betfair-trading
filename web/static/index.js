
var PTRADE_ON_TEXT = 'Trading..';
var PTRADE_OFF_TEXT = 'Trade';

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

function update_ptrading(ptrading_new) {
    ptrading = ptrading_new.map(function(s) {return s.strategy_id;});
}

function paper_trade() {
    var strat_id = $(this).attr('data-strat-id');
    var $this = $(this);
    if($.inArray(strat_id, ptrading) == -1) {
        $.ajax({
            'url': '/api/paper/add/' + strat_id,
            'success': function() {
                $this.removeClass('ptrade-off').addClass('ptrade-on btn-success').html(PTRADE_ON_TEXT);
                $.ajax({
                    url: '/api/paper/strategies',
                    success: update_ptrading
                });
            }
        });
    } else {
        $.ajax({
            'url': '/api/paper/remove/' + strat_id,
            'success': function() {
                $this.removeClass('ptrade-on').removeClass('btn-success').removeClass('btn-danger')
                    .addClass('ptrade-off').html(PTRADE_OFF_TEXT);
                $.ajax({
                    url: '/api/paper/strategies',
                    success: update_ptrading
                });
            }
        });

    }
}


$(function() {
    ptrading = ptrading.map(function(s) {return s.strategy_id;})
    $('#scorecards_table').dataTable({
        'sDom': "<'row-fluid'<'span6'l><'span6'f>r>t<'row-fluid'<'span6'i><'span6'p>>",
        'bProcessing': true,
        'aaData': scorecards,
        'sAjaxDataProp': '',
        'aoColumns': [
            {
                'sTitle': 'Timestamp',
                'mData': function(source, type, val) {
                    if(typeof type === 'undefined') {
                        source.timestamp = moment(source['timestamp']);
                    }

                    if (type === 'display' || type === 'filter') {
                        return  source.timestamp.format("YYYY-MM-DD HH:mm");
                    }
                    return source.timestamp;
                }
            },
            {
                sTitle: 'Paper Trade',
                mData: function(source) {
                    var $button = $('<button></button>').attr({"type": "button", "data-strat-id": source['strategy_id']})
                                                        .addClass('btn btn-small').width('80%');

                    if($.inArray(source['strategy_id'], ptrading) > -1) {
                        $button.addClass('btn-success ptrade-on');
                        $button.html(PTRADE_ON_TEXT);
                    } else {
                        $button.addClass('ptrade-off');
                        $button.html(PTRADE_OFF_TEXT);
                    }
                    return $button[0].outerHTML;
                }
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
        fnDrawCallback: function() {
            $('button').mouseenter(function () {
                var $this = $(this);
                if($this.hasClass('ptrade-on')) {
                    $this.removeClass('btn-success').addClass('btn-danger').html('Stop');
                } else if ($this.hasClass('ptrade-off')) {
                    $this.addClass('btn-success').html('Start');
                }
            }).mouseleave(function () {
                    var $this = $(this);
                    if($this.hasClass('ptrade-on')) {
                        $this.removeClass('btn-danger').addClass('btn-success').html(PTRADE_ON_TEXT);
                    } else if ($this.hasClass('ptrade-off')) {
                        $this.removeClass('btn-success').html(PTRADE_OFF_TEXT);
                    }
            }).click(paper_trade);

            $('button.ptrade-off').mouseenter(function () {

            }).mouseleave(function () {

            })
        },
        'bAutoWidth':false,
        'sPaginationType':'bootstrap',
        "iDisplayLength": 50
    });
});
