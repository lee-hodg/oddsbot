#!/usr/bin/env python
from betdaq import api
import re

# NB my betdaq api is customised from pybetdaq, so prob
# best to move from venv to Exchanges dir to make more obv.

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


# =====================HELPER FUNCS
def breaker(pieceSize, L):  # pieceSize non-zero integer

    '''
    Break a list into pieceSize pieces.
    For use when submitting multiple market
    Ids to API at once, without sending too many.
    '''
    broken = []

    while L:
        if len(L) > pieceSize:
            broken.append(L[:pieceSize])
            L = L[pieceSize:]
        else:
            broken.append(L[:])
            return broken
    return broken


# NB to install pybetdaq, just manually the betdaq folder into the venv
# /path/to/venv/lib/python2.7/site-packages/betdaq
# Also because you use the uk API you might want to set
# WSDLLOCAL = 'http://api.betdaq.co.uk/v2.0/API.wsdl'
# (you should really dload this file and use that locally, but for now
# at least that didn't seem to work, it kept on using the api.betdaq.com
# endpoints)

# Login details
api.set_user('lordgranville', 'SZCunX5kv0')

# Get Sport
sport_id = None
sports = api.ListTopLevelEvents()
sids = [s.id for s in sports if s.name in ['Soccer']]

# Get markets for that sport
if sids:
    markets = api.GetEventSubTreeWithSelections(sids)
else:
    log.error('No sport id found. Exit()')
    exit()


# I added parentEventId to Market Object and changed the parser to put in there
# Now can group the markets by event they correspond to with
# from collections import defaultdict
# omarkets = defaultdict(list)
# for m in markets:
#     epid = m.parentEventId
#     omarkets[epid].append(m)
# # Back to regular dict
# markets = dict(omarkets)

# ============= Organize/group markets under common event
# This will save time in arb finder as it will just number of times
# need to compare event name/team names.
eventsMkts = {}
marketIdList = []
for market in markets:
    # Event data
    exchangeName = 'Betdaq'
    eventid = market.parentEventId
    eventName = market.name.rsplit('|')[-2]
    # Remove brackets
    eventName = re.sub(r'\([^)]*\)', '', eventName).strip()
    dateTime = market.startTime.strftime('%Y-%m-%d %H:%M')
    try:
        # Add shortDateTime too for easier comparison with bookie
        shortDateTime = market.startTime.strftime('%m %d')
    except ValueError as e:
        log.error(e)
        shortDateTime = ''
    try:
        team1, team2 = eventName.split(' v ')
    except ValueError:
        team1 = ''
        team2 = ''
    try:
        compName = market.name.rsplit('|')[-3]
    except KeyError:
        compName = ''

    # If Event not already there, append
    if eventid in eventsMkts.keys():
        # just append new mkt data
        pass
    else:
        # create the event and associated date
        # then append mkt data later
        eventsMkts[eventid] = {'exchangeName': exchangeName,
                               'eventName': eventName,
                               'dateTime': dateTime,
                               'shortDateTime': shortDateTime,
                               'team1': team1,
                               'team2': team2,
                               'compName': compName,
                               'markets': {}
                               }

    # Now create market dict and append that too
    marketId = market.id
    marketIdList.append(marketId)
    try:
        marketName = market.name.rsplit('|')[-1]
    except KeyError:
        marketName = ''

    # Runner names and selectionIds
    # Index runners by selectionId (needed to match the runnerName to price
    # data later, especially in complicated markets)
    runners = {}
    MOnames = ['HOME', 'DRAW', 'AWAY']  # translate match odds runner names.
    resRunners = market.selections
    if marketName == 'Match Odds':
        # Instead of using team names and 'The Draw'
        # use Home Draw Away.
        for posn, runner in enumerate(resRunners):
            sid = str(runner.id)
            try:
                runners[sid] = {'runnerName': MOnames[posn]}
            except IndexError:
                log.error('IndexError. Exchanging runnerNames to home, away'
                          ' draw. Are there 3 runners? Logout Exit')
                exit()
    elif marketName == 'Correct Score':
        # Format 1 - 0 as 1-0
        for runner in resRunners:
            sid = str(runner.id)
            print 'Init runnerName: %s' % runner.name
            runnerName = runner.name.rsplit('|')[-1]
            print 'Split | take last: %s' % runnerName
            # Remove brackets
            runnerName = re.sub(r'\([^)]*\)', '', runnerName).strip()
            print 'Remove brackets, strip: %s' % runnerName
            # Want only score not name
            if team2 in runnerName:
                # Remove then reverse
                runnerName = runnerName.rsplit()[-1]  # Only score not name
                print 'Split on whitespace take last: %s' % runnerName
                # Reverse
                score1, score2 = runnerName.split('-')
                runnerName = '-'.join([score2, score1])
                print 'Split - on score reverse: %s' % runnerName
            elif 'Any Other Score' in runnerName:
                runnerName = runnerName.split('-')[0]
            else:
                runnerName = runnerName.rsplit()[-1]  # Only score not name

            runners[sid] = {'runnerName': runnerName, }
    else:
        for runner in resRunners:
            sid = str(runner.id)
            runnerName = runner.name.rsplit('|')[-1]
            runners[sid] = {'runnerName': runnerName, }

    marketDic = {'marketName': marketName,
                 'runners': runners,
                 'marketId': marketId,
                 }

    # Finally add the marketDic
    eventsMkts[eventid]['markets'][marketId] = marketDic

# Get prices for the markets
# Remember the objects returned are really Price objects
# and you can access for and against prices as attribs
# layprices
# ============= GET PRICES DATA
# Now we have all the marketIds, we break the list
# into smaller chunks of e.g. 50(the max?). Then we
# can request book data batch of 50 at a time.
# brokenMarketIdList = breaker(50, marketIdList)
mkt_selections = []
#for subList in brokenMarketIdList:
#   mkt_selections.append(api.GetPrices(subList))
# Hitting API throttling problems, hmmm....
# mkt_selections.extend(api.GetPrices(brokenMarketIdList[0]))
# I think the api method will already chunk to 50 and throttle between
mkt_selections = api.GetPrices(marketIdList)

# Now take the data of interest from marketBookResList,
# and augment the associated event in eventsList.
for mkt in mkt_selections:
    if mkt:
        # Get mid from first runner
        b_mid = mkt[0].mid
    else:
        continue
    # Match up mkt with eventsMkts
    for eventId, event in eventsMkts.items():
        if b_mid in event['markets'].keys():
            e_market = event['markets'][b_mid]
            print eventId
            for sel in mkt:
                sid = str(sel.id)
                # So far runnders sid contains runner name only
                availableToLay = []
                for laytuple in sel.layprices:
                    price, size = laytuple
                    availableToLay.append({'price': price, 'size': size})
                e_market['runners'][sid]['availableToLay'] = availableToLay

# Instead of json dump, I will use pymongo to write to mongo
# But let's clean up schema first (get rid of keying)
eventsMktsList = list(eventsMkts.values())
for event in eventsMktsList:
    event['markets'] = event['markets'].values()
    for market in event['markets']:
        market['runners'] = market['runners'].values()
# Clear old and insert
xevents.remove({'exchangeName': 'Betdaq'})
xevents_ids = xevents.insert(eventsMktsList)
