from __future__ import print_function, division

import logging
import datetime
import requests
from bs4 import BeautifulSoup as BS
import pandas as pd


HORSERACEBASE_RESULTS_URL = 'http://www.horseracebase.com/excelresults.php'

dt = datetime.datetime

def scrape_sportinglife():
    url = "http://www.sportinglife.com/ajax/racing/results-search?" + \
                "course-id=1510&racename=&date-range=period&page=2&fromDate=25/12/2005&toDate=01/01/2012"

    r = requests.get(url)

    if r.status_code == 200:
        doc = BS(r.content)
        links = [li.find('a')['href'] for li in doc.find_all('li')]
    else:
        links = []
    print(links)
    for l in links:
        if not l.startswith('/racing'):
            continue
        r = requests.get('http://www.sportinglife.com' + l)
        doc = BS(r.content)
        trs = doc.find('table').find('tbody').find_all('tr')
        f = filter(lambda x: x is not None, map(lambda x: x[2].get_text().split('\n')[3].strip() if len(x) >= 3 else None, [x.find_all('td') for x in trs]))
        print(f)


#drange = pd.date_range(dt(2010, 1, 1), dt(2013, 2, 13))[::-1]
#for d in drange:

def racecards_horseracebase(date, path=None):
    date_str = date.strftime('%Y-%m-%d')
    logging.info('Downloading historical racecard for %s' % date_str)
    res = requests.post(HORSERACEBASE_RESULTS_URL, data={'user': '19171', 'racedate': date_str})
    assert res.status_code == 200
    if path is None:
        path = res.headers['content-disposition'].split(';')[1].split('=')[1].split('.')[0].strip() + '.csv'
    logging.info('The download was successful, saving data to %s' % path)
    open(path, 'w').write(res.content)

