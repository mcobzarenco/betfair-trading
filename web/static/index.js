
function render_scorecard(card, a, b) {
    $('#card').html(card['lik']);
}

function render_bets(bets) {
    $('#bets_table').html(bets);
}

function scorecard_table(scorecard) {
    $('#scorecards_table').html(scorecard);
    $('.dataframe').dataTable();
    $('.dataframe').addClass('table');
}


function err(data, a, b) {
    var i = 0;
}


$(function() {
    $.ajax({
        'url': '/scorecards',
        'success': scorecard_table,
        'error': err
    })
});