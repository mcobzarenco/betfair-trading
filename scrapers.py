from __future__ import print_function, division

import datetime
import requests
from bs4 import BeautifulSoup as BS
import pandas as pd


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


dt = datetime.datetime
drange = pd.date_range(dt(2010, 1, 1), dt(2013, 2, 13))[::-1]
for d in drange:
    print('doing %s' % d)
    res = requests.post('http://www.horseracebase.com/excelresults.php', data={'user': '19171', 'racedate': d.strftime('%Y-%m-%d')})
    assert res.status_code == 200
    name = res.headers['content-disposition'].split(';')[1].split('=')[1].split('.')[0].strip() + '.csv'
    print('name=%s' % name)
    open(name, 'w').write(res.content)

