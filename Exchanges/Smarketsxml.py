#!/usr/bin/env python
# Use the faster c implementation
import xml.etree.cElementTree as ET
import urllib2
import datetime

# ======================MONGO
# Now can easily insert documents with xmarket_id = xmarkets.insert(someevent)
# (see http://api.mongodb.org/python/current/tutorial.html)
from pymongo import MongoClient
client = MongoClient()
client = MongoClient('localhost', 27017)
db = client.oddsbot_scrapy  # connect to our db
xevents = db.xevents  # then exchange_events collection


# ======================LOGGING
import logging
LOG_LEVEL = logging.DEBUG
LOGFORMAT = "  %(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s"
from colorlog import ColoredFormatter
logging.root.setLevel(LOG_LEVEL)
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)
log = logging.getLogger('pythonConfig')
log.setLevel(LOG_LEVEL)
log.addHandler(stream)


log.info('BEGINING SMARKETS SCRAPE')
# Just soccer
log.info('Openining feed..')
# feed = urllib.urlopen("http://smarkets.s3.amazonaws.com/oddsfeed.xml")
request = urllib2.Request("http://smarkets.s3.amazonaws.com/oddsfeed.xml")
request.add_header('Accept-encoding', 'gzip')
feed = urllib2.urlopen(request)

# Data is compressed (which is good for bandwidth so don't bother using requests
# lib to get non-compressed version)
log.info('Read to compressed..')
compressed_data = feed.read()
import StringIO
log.info('compressed to string buffer')
compressedstream = StringIO.StringIO(compressed_data)
import gzip
log.info('Build gzip file')
gzipper = gzip.GzipFile(fileobj=compressedstream)

# Parse XML
log.info('Parsing feed to tree..')
# Pass is xml string
# tree = ET.fromstring(gzipper.read())
# Pass it file like object
tree = ET.parse(gzipper)
root = tree.getroot()

log.info('Creating event list schema..')
events = []
for match in root.findall('./event[@type="Football match"]'):
    eventName = match.get('name')
    try:
        team1, team2 = eventName.split(' vs. ')
    except ValueError:
        team1 = ''
        team2 = ''
    try:
        dt = datetime.datetime.strptime(match.get('date'), '%Y-%m-%d').date()
        shortDateTime = dt.strftime('%m %d')
    except (ValueError, TypeError):
        shortDateTime = ''
    try:
        time = datetime.datetime.strptime(match.get('time'), '%H:%M:%S').time()
    except (ValueError, TypeError):
        time = None
    # combine time and date to datetime
    if time:
        dateTime = datetime.datetime.combine(dt, time).strftime('%Y-%m-%d %H:%M')
    else:
        dateTime = match.get('date')

    eventDic = {'exchangeName': 'Smarkets',
                'sport': 'Football',
                'eventId': match.get('id'),
                'url': match.get('url'),
                'eventName': eventName,
                'team1': team1,
                'team2': team2,
                'compName': match.get('parent'),
                'dateTime': dateTime,
                'shortDateTime': shortDateTime,
                'markets': []
                }
    for market in match.findall('market'):
        marketName = market.get('slug')
        if marketName == 'winner':
            marketName = 'Match Odds'
        elif marketName == 'correct-score':
            marketName = 'Correct Score'
        elif marketName == 'half-time-score':
            marketName = 'Half Time Correct Score'
        marketDic = {'marketName': marketName,
                     'marketId': market.get('id'),
                     'runners': []
                     }
        for selection in market.findall('contract'):
            runnerName = selection.get('name')
            if marketName == 'Match Odds':
                # could use selection.get('slug') == 'home' etc too
                if team1 in runnerName:
                    runnerName = 'HOME'
                elif 'draw' in runnerName.lower():
                    runnerName = 'DRAW'
                elif team2 in runnerName:
                    runnerName = 'AWAY'
            elif marketName in ['Correct Score', 'Half Time Correct Score']:
                # Format 1 - 0 as 1-0
                # Remove brackets
                runnerName = runnerName.replace(' ', '')
            runnerDic = {'runnerName': runnerName,
                         'availableToLay': [],
                         }
            prices = selection.findall('./bids/price')
            if prices:
                for price in prices:
                    runnerDic['availableToLay'].append({'price': price.get('decimal'),
                                                        'size': price.get('backers_stake')
                                                        })
            marketDic['runners'].append(runnerDic)
        eventDic['markets'].append(marketDic)
    events.append(eventDic)

# Write to mongodb
xevents.remove({'exchangeName': 'Smarkets'})
xevents_ids = xevents.insert(events)
log.info('Inserted %i entries' % len(xevents_ids))
