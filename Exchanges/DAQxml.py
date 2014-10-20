#!/usr/bin/env python
# Use the faster c implementation
import xml.etree.cElementTree as ET
import urllib
import datetime
import re

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


log.info('BEGINING BETDAQ SCRAPE')
# Just soccer
log.info('Openining feed..')
feed = urllib.urlopen("http://xml.betdaq.com/soccer")

# Parse XML
log.info('Parsing feed to tree..')
tree = ET.parse(feed)
root = tree.getroot()

log.info('Creating event list schema..')
events = []
for sport in root.find('SPORT'):
    for country in sport.iter('EVENT'):
        for league in country.iter('SUBEVENT'):
            for match in league.iter('SUBEVENT1'):
                eventName = match.get('NAME')
                # Remove anything with brackets like (Fri) or (Live)
                eventName = re.sub(r'\([^)]*\)', '', eventName).strip()
                # If there is an unbracketed time like HH:MM at start now remove
                # that too
                eventName = re.sub(r'^([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]',
                                   '', eventName).strip()
                try:
                    team1, team2 = eventName.split(' v ')
                except ValueError:
                    team1 = ''
                    team2 = ''
                try:
                    dt = datetime.datetime.strptime(match.get('DATE'), '%Y-%m-%d %H:%M:%S')
                    shortDateTime = dt.strftime('%m %d')
                except (ValueError, TypeError):
                    shortDateTime = ''
                eventDic = {'exchangeName': 'Betdaq',
                            'sport': sport.get('NAME'),
                            'eventName': eventName,
                            'team1': team1,
                            'team2': team2,
                            'compName': league.get('NAME'),
                            'dateTime': match.get('DATE'),
                            'shortDateTime': shortDateTime,
                            'markets': []
                            }
                for market in match.iter('MARKET'):
                    marketDic = {'marketName': market.get('NAME'),
                                 'marketId': market.get('ID'),
                                 'runners': []
                                 }
                    for selection in market.findall('SELECTION'):
                        runnerName = selection.get('NAME')
                        if market.get('NAME') == 'Match Odds':
                            if team1 in runnerName:
                                runnerName = 'HOME'
                            elif 'draw' in runnerName.lower():
                                runnerName = 'DRAW'
                            elif team2 in runnerName:
                                runnerName = 'AWAY'
                        elif market.get('NAME') == 'Correct Score':
                            # Format 1 - 0 as 1-0
                            # Remove brackets
                            runnerName = re.sub(r'\([^)]*\)', '', runnerName).strip()
                            # Want only score not name
                            if team2 in runnerName:
                                # Remove then reverse
                                runnerName = runnerName.rsplit()[-1]  # Only score not name
                                # Reverse
                                score1, score2 = runnerName.split('-')
                                runnerName = '-'.join([score2, score1])
                            elif 'Any Other Score' in runnerName:
                                runnerName = runnerName.split('-')[0]
                            else:
                                runnerName = runnerName.rsplit()[-1]  # Only score not name

                        runnerDic = {'runnerName': runnerName,
                                     'availableToLay': [],
                                     }
                        for outcome in selection.findall('.//ODDS[@POLARITY="LAY"]'):
                            for price in outcome:
                                runnerDic['availableToLay'].append({'price': price.get('VALUE'),
                                                                    'size': price.find('./AMOUNT[@CURRENCY="GBP"]').get('VALUE')
                                                                    }
                                                                   )
                        marketDic['runners'].append(runnerDic)
                    eventDic['markets'].append(marketDic)
                events.append(eventDic)

# Write to mongodb
xevents.remove({'exchangeName': 'Betdaq'})
xevents_ids = xevents.insert(events)
log.info('Inserted %i entries' % len(xevents_ids))
