
/* Default class modification */
$.extend($.fn.dataTableExt.oStdClasses, {
    "sWrapper":"dataTables_wrapper form-inline"
});


/* API method to get paging information */
$.fn.dataTableExt.oApi.fnPagingInfo = function (oSettings) {
    return {
        "iStart":oSettings._iDisplayStart,
        "iEnd":oSettings.fnDisplayEnd(),
        "iLength":oSettings._iDisplayLength,
        "iTotal":oSettings.fnRecordsTotal(),
        "iFilteredTotal":oSettings.fnRecordsDisplay(),
        "iPage":Math.ceil(oSettings._iDisplayStart / oSettings._iDisplayLength),
        "iTotalPages":Math.ceil(oSettings.fnRecordsDisplay() / oSettings._iDisplayLength)
    };
}


/* Bootstrap style pagination control */
$.extend($.fn.dataTableExt.oPagination, {
    "bootstrap":{
        "fnInit":function (oSettings, nPaging, fnDraw) {
            var oLang = oSettings.oLanguage.oPaginate;
            var fnClickHandler = function (e) {
                e.preventDefault();
                if (oSettings.oApi._fnPageChange(oSettings, e.data.action)) {
                    fnDraw(oSettings);
                }
            };

            $(nPaging).addClass('pagination').append(
                '<ul>' +
                    '<li class="prev disabled"><a href="#">&larr; ' + oLang.sPrevious + '</a></li>' +
                    '<li class="next disabled"><a href="#">' + oLang.sNext + ' &rarr; </a></li>' +
                    '</ul>'
            );
            var els = $('a', nPaging);
            $(els[0]).bind('click.DT', { action:"previous" }, fnClickHandler);
            $(els[1]).bind('click.DT', { action:"next" }, fnClickHandler);
        },

        "fnUpdate":function (oSettings, fnDraw) {
            var iListLength = 5;
            var oPaging = oSettings.oInstance.fnPagingInfo();
            var an = oSettings.aanFeatures.p;
            var i, j, sClass, iStart, iEnd, iHalf = Math.floor(iListLength / 2);

            if (oPaging.iTotalPages < iListLength) {
                iStart = 1;
                iEnd = oPaging.iTotalPages;
            }
            else if (oPaging.iPage <= iHalf) {
                iStart = 1;
                iEnd = iListLength;
            } else if (oPaging.iPage >= (oPaging.iTotalPages - iHalf)) {
                iStart = oPaging.iTotalPages - iListLength + 1;
                iEnd = oPaging.iTotalPages;
            } else {
                iStart = oPaging.iPage - iHalf + 1;
                iEnd = iStart + iListLength - 1;
            }

            for (i = 0, iLen = an.length; i < iLen; i++) {
                // Remove the middle elements
                $('li:gt(0)', an[i]).filter(':not(:last)').remove();

                // Add the new list items and their event handlers
                for (j = iStart; j <= iEnd; j++) {
                    sClass = (j == oPaging.iPage + 1) ? 'class="active"' : '';
                    $('<li ' + sClass + '><a href="#">' + j + '</a></li>')
                        .insertBefore($('li:last', an[i])[0])
                        .bind('click', function (e) {
                            e.preventDefault();
                            oSettings._iDisplayStart = (parseInt($('a', this).text(), 10) - 1) * oPaging.iLength;
                            fnDraw(oSettings);
                        });
                }

                // Add / remove disabled classes from the static elements
                if (oPaging.iPage === 0) {
                    $('li:first', an[i]).addClass('disabled');
                } else {
                    $('li:first', an[i]).removeClass('disabled');
                }

                if (oPaging.iPage === oPaging.iTotalPages - 1 || oPaging.iTotalPages === 0) {
                    $('li:last', an[i]).addClass('disabled');
                } else {
                    $('li:last', an[i]).removeClass('disabled');
                }
            }
        }
    }
});

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
