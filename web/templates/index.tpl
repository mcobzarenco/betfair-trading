<!DOCTYPE html>
<html>
<link href="/static/libs/bootstrap.min.css" rel="stylesheet">
<link href="/static/libs/dataTables-bootstrap.css" rel="stylesheet">
<script src="/static/libs/jquery-1.9.1.js"></script>
<script src="/static/libs/DataTables-1.9.4/media/js/jquery.dataTables.js"></script>
<script src="/static/libs/dataTables-bootstrap.js"></script>
<script type="text/javascript" >
    var scorecards = {{!json_scorecards}};
</script>
<script type="text/javascript" src="/static/index.js"></script>
<head>
    <title>Backtests</title>
</head>
<body>
<div class="container-fluid" style="width: 90%; margin-left: auto; margin-right: auto;">
    <div class="row-fluid">
        <div class="span12" style="padding-top: 10px">
            <ul class="nav nav-pills">
                <li class="active">
                    <a href="#">Backtests</a>
                </li>
                <li><a href="/paper">Paper Trading</a></li>
            </ul>
        </div>
    </div>
    <div class="row-fluid">
        <div class="span12">
            <h3>Backtests</h3>
        </div>
    </div>
    <table id="scorecards_table" class="table table-striped table-condensed"></table>
</div>

</body>
</html>
