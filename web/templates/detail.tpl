<!DOCTYPE html>
<html>
<link href="/static/libs/bootstrap.min.css" rel="stylesheet">
<link href="/static/detail.css" rel="stylesheet">
<script src="/static/libs/jquery-1.9.1.js"></script>
<script src="/static/libs/highstock.js"></script>

<script type="text/javascript" >
    var scorecard = JSON.parse({{!json_scorecard}});
</script>
<script type="text/javascript" src="/static/detail.js"></script>
<head>
    <title></title>
</head>
<body>

<div class="container-fluid" style="width: 90%; margin-left: auto; margin-right: auto;">
    <div class="row-fluid">
        <div class="span12">
            <h3> Scorecard <span class="scorecard_id"></span></h3>
        </div>
    </div>
    <div class="row-fluid">
        <div class="span4" id="llik_series">
            <p style="font-size: 80%; padding-bottom: 5px;">
                Generated at <span id="timestamp"></span> (backtest took <span id="time_taken"></span> seconds)
            </p>
            <div class="row-fluid">
                <div class="span6" id="params_ts"></div>
                <div class="span6" id="params_risk"></div>
            </div>
        </div>
        <div class="span8" id="daily_pnl"></div>
    </div>
    <div class="row-fluid">
        <div class="span4" id="all_series"></div>
        <div class="span4" id="backs_series"></div>
        <div class="span4" id="lays_series"></div>
    </div>
    <div class="row-fluid">
        <div class="span4" id="events_series"></div>
    </div>
    <div class="row-fluid">

    </div>
</div>

</body>
</html>
