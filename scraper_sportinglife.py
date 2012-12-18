import requests
from bs4 import BeautifulSoup as BS

url = "http://www.sportinglife.com/ajax/racing/results-search?" + \
            "course-id=1510&racename=&date-range=period&page=2&fromDate=25/12/2005&toDate=01/01/2012"

r = requests.get(url)

if r.status_code == 200:
    doc = BS(r.content)
    links = [li.find('a')['href'] for li in doc.find_all('li')]
else:
    links = []
links
for l in links:
    if not l.startswith('/racing'):
        continue
    r = requests.get('http://www.sportinglife.com' + l)
    doc = BS(r.content)
    trs = doc.find('table').find('tbody').find_all('tr')
    f = filter(lambda x: x is not None, map(lambda x: x[2].get_text().split('\n')[3].strip() if len(x) >= 3 else None, [x.find_all('td') for x in trs]))
    print(f)
