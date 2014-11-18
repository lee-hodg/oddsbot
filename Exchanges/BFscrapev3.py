#!/usr/bin/env python
from bet_face import loginAPI, logoutAPI, getEventTypes, listMarketBook, listEvents
from bet_face import listMarketCatalogue
import sys
import datetime
import os

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


# ======================= HELPER FUNCTIONS
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


def eventIdBreaker(eventsList):
    '''
    events come with an Id and a marketCount.
    When we make the call to listMarketCatalogue it
    will return at most 1000 markets.
    This means we need to intelligently break the
    events list in such a way each batch is <=1000
    markets.
    '''
    eventIds = []
    subList = []
    mCounter = 0
    eventCnt = 0  # debug only
    for event in eventsList:
        eventCnt += 1
        if event['marketCount'] < 1000:
            # Ignore events that themselves have over 1000
            # (unlikely anyway)
            mCounter += event['marketCount']
            if mCounter < 1000:
                subList.append((event['event']['id'], event['marketCount']))
                # subList.append(event['event']['id'])
            else:
                eventIds.append(subList)
                subList = [(event['event']['id'], event['marketCount'])]
                # subList = [event['event']['id'], ]
                mCounter = event['marketCount']

    # Remember to append final subList
    if subList:
        eventIds.append(subList)
    # print 'I counted %i events' % eventCnt
    return eventIds

# ==================== API PARAMS
url = "https://api.betfair.com/exchange/betting/json-rpc/v1"
MAX_RES = '1000'  # Number of markets to grab with listMarketCatalogue

# ====================LOGIN
# Perform login and get sessionToken
# Use delayed key for testing, get from API-NG visualiser
# but SWITCH in poduction! (https://api-ng.betstores.com/account/)
# Ideally, it would be nice to md5 hash password
# but it does not seem to work.
# We check for cmdline arg for sessToken, else use login func
# to generate.

appKey = 'oqHPNFV7vwlvKZKx'  # non-delayed
# appKey = 'HuuyZUoVt9raEOOh'  # delayed
# try:
#     username = os.environ.get('betfair_username')
#     password = os.environ.get('betfair_password')
# except KeyError:
#     log.error('Betfair username and password should be set as env vars.')
#     exit()
try:
    with open('/home/lee/thevault/bf.txt') as f:
        username, password = f.read().split()
except IOError:
    try:
        # local non-server install
        username = os.environ.get('betfair_username')
        password = os.environ.get('betfair_password')
    except KeyError:
        log.error('Could not read user, pass from file or env.')
        exit()


payload = 'username=%s&password=%s' % (username, password)
login_headers = {'X-Application': 'arbOracle', 'Content-Type': 'application/x-www-form-urlencoded'}

# Perform login to get session token unless user has specified it as cmd arg.
args = len(sys.argv)
if (args < 2):
    # if user not entered session key at cmdline
    loginresult = loginAPI(payload, login_headers)
    sessionToken = loginresult['sessionToken']
    # sessionToken = raw_input('Enter your session Token/SSOID :')
else:
    sessionToken = sys.argv[1]

# Generate headers with sessionToken:
headers = {'X-Application': appKey, 'X-Authentication': sessionToken,
           'content-type': 'application/json', 'Accept': 'application/json'}


log.info('BEGINING BETFAIR SCRAPE')
# ======================= EVENT LISTING INFO
# List number of events that match filter,
# NB. football has eventTypeID 1. Use
# printEventTypeID(..) with result of getEventTypes(..)
# (with no filter) to get all eventTypeIDs

efilter = {'eventTypeIds': ['1', ],
           'marketTypeCodes': ['MATCH_ODDS', 'CORRECT_SCORE']
           }
eventInfo = getEventTypes(url, headers, efilter)

if eventInfo == -1:
    # There was an error
    log.error('Error occured getting EventTypes. Log out. Exit')
    logoutAPI(headers)
    exit()
else:
    # print json.dumps(eventInfo, indent=4)
    # Print events and Ids
    # printEventTypeID(eventInfo)  # use no filter when obtaining eventInfo
    log.info('The numer of %s markets is %i' %
             (eventInfo['result'][0]['eventType']['name'],
              eventInfo['result'][0]['marketCount'],)
             )


# ===============listEvents
# The idea is to grab the list of events, then
# request the market date in batches with the event ids
# (this will stop the problem of having to page over 1000
# max results returned from listMarketCatalogue, and the problems
# associated, such as if 1000 events have same date...infinite loops,
# duplicates etc)
# Typical return looks like
# {u'event': {u'countryCode': u'GB',
#   u'id': u'27282393',
#   u'name': u'Rotherham v Leeds',
#   u'openDate': u'2014-10-17T18:45:00.000Z',
#   u'timezone': u'Europe/London'},
#  u'marketCount': 13}
eventFilter = {"eventTypeIds": ['1'],
               "marketTypeCodes": ['MATCH_ODDS', 'CORRECT_SCORE'],
               }
eventsList = listEvents(url, headers, eventFilter)
if eventsList != -1:
    try:
        eventsList = eventsList['result']
    except KeyError:
        log.error('eventsList no results. Logout. Exit.')
        logoutAPI(headers)
        exit()
else:
    log.error('listEvents returned -1. Logout. Exit.')
    logoutAPI(headers)
    exit()
log.info('Grabbed %i events' % len(eventsList))


# =============== MarketCatalogue v2
# eventList may have ~1500 events in it (each having n marketCount)
# listMarketCatalogue has a limit of 1000 markets suggesting blocks of 30
# might be about right for a batch request. In my test max was 76 min was 1. Mean
# was 10.
marketCatalogueList = []
# market count before breaking
preBreakingMktsCount = sum([int(event['marketCount']) for event in eventsList])
log.info('Total mkts count before breaking is %i' % preBreakingMktsCount)
brokenEvents = eventIdBreaker(eventsList)
totalMktsCount = sum([int(pair[1]) for el in brokenEvents for pair in el])
# Should now match eventInfo['result'][0]['marketCount']
log.info('Total mkts count after breaking is %i' % totalMktsCount)
maxRes = MAX_RES
projection = ["EVENT", "COMPETITION", "RUNNER_DESCRIPTION"]
for subList in brokenEvents:
    subMktsCount = sum([int(pair[1]) for pair in subList])
    log.info('Will call listMarketCatalogue on subList of %i events'
             ' with %i markets' % (len(subList), subMktsCount))
    eventIds = [pair[0] for pair in subList]
    marketCatalogueFilter = {'eventIds': eventIds,
                             'marketTypeCodes': ["MATCH_ODDS", 'CORRECT_SCORE'],
                             }
    marketCatalogue = listMarketCatalogue(url, headers,
                                          marketCatalogueFilter,
                                          maxRes,
                                          projection,
                                          sort='FIRST_TO_START')
    try:
        # also if returned in error with -1 exception triggered here.
        marketCatalogueResJSON = marketCatalogue['result']
        marketCatalogueList.extend(marketCatalogueResJSON)
    except KeyError as e:
        log.error('KeyError for marketCatalogueResult: \n%s' % e)
        logoutAPI(headers)
        exit()
    except TypeError as e:
        log.error('Type for marketCatalogueResult: \n%s' % e)
        log.error(marketCatalogue)
        logoutAPI(headers)
        exit()

# ============= Organize/group markets under common event
# This will save time in arb finder as it will just number of times
# need to compare event name/team names.
eventsMkts = {}
marketIdList = []
nocompdataIds = []
for market in marketCatalogueList:
    # Event data
    exchangeName = 'Betfair'
    eventid = market['event']['id']
    eventid = eventid.replace('.', '@')  # mongo doesn't allow period in key
    eventName = market['event']['name']
    dateTime = market['event']['openDate']
    try:
        # Add shortDateTime too for easier comparison with bookie
        openDate = datetime.datetime.strptime(market['event']['openDate'],
                                              '%Y-%m-%dT%H:%M:%S.%fZ')
        shortDateTime = openDate.strftime('%m %d')
    except ValueError as e:
        log.error(e)
        shortDateTime = ''
    try:
        team1, team2 = eventName.split(' v ')
    except ValueError:
        team1 = ''
        team2 = ''
    try:
        compName = market['competition']['name']
    except KeyError:
        compName = ''
        # log.error('There was no competition name for event with marketId %s'
        #           % resN['marketId'])
        nocompdataIds.append(market['marketId'])  # debug only

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
    marketId = market['marketId']
    marketIdList.append(marketId)
    marketId = marketId.replace('.', '@')  # mongo does not allow period in key
    try:
        totalMatched = str(market['totalMatched'])
    except KeyError:
        totalMatched = ''
    try:
        marketName = market['marketName']
    except KeyError:
        marketName = ''

    # Runner names and selectionIds
    # Index runners by selectionId (needed to match the runnerName to price
    # data later, especially in complicated markets)
    runners = {}
    MOnames = ['HOME', 'AWAY', 'DRAW']  # translate match odds runner names.
    resRunners = market['runners']
    if marketName == 'Match Odds':
        # Instead of using team names and 'The Draw'
        # use Home Draw Away.
        for posn, runner in enumerate(resRunners):
            sid = str(runner['selectionId'])
            try:
                runners[sid] = {'runnerName': MOnames[posn]}
            except IndexError:
                log.error('IndexError. Exchanging runnerNames to home, away'
                          ' draw. Are there 3 runners? Logout Exit')
                logoutAPI(headers)
                exit()
    elif marketName == 'Correct Score':
        # Format 1 - 0 as 1-0
        for runner in resRunners:
            sid = str(runner['selectionId'])
            runners[sid] = {'runnerName': runner['runnerName'].replace(' ', ''), }
    else:
        for runner in resRunners:
            sid = str(runner['selectionId'])
            runners[sid] = {'runnerName': runner['runnerName'], }

    marketDic = {'totalMatched': totalMatched,
                 'marketName': marketName,
                 'runners': runners,
                 'marketId': marketId,
                 }

    # Finally add the marketDic
    eventsMkts[eventid]['markets'][marketId] = marketDic


# ============= GET PRICES DATA

log.info('Starting forage at: %s' % datetime.datetime.now().strftime('%H:%M:%S'))

# Now we have all the marketIds, we break the list
# into smaller chunks of e.g. 30. Then we
# can request book data batch of 30 at a time.
brokenMarketIdList = breaker(30, marketIdList)
marketBookResList = []
price_proj = {"priceData": ["EX_BEST_OFFERS"], "virtualise": "true",
              "exBestOffersOverrides": {"bestPricesDepth": 3}
              }
for subList in brokenMarketIdList:
    marketBooksJSON = listMarketBook(url, headers, price_proj, *subList)
    try:
        # also if returned in error with -1 exception triggered here.
        marketBooksResJSON = marketBooksJSON['result']
        marketBookResList.extend(marketBooksResJSON)
    except KeyError as e:
        log.error('KeyError for marketBookResult: \n%s' % e)
        logoutAPI(headers)
        exit()
    except TypeError as e:
        # When `marketBooksJSON == 1`.
        log.error('Type for marketBookResult: \n%s' % e)
        logoutAPI(headers)
        exit()

# Now take the data of interest from marketBookResList,
# and augment the associated event in eventsList.
for bookRes in marketBookResList:
    b_mid = bookRes['marketId']
    b_mid = b_mid.replace('.', '@')  # mongo doesn't allow period in key
    for eventId, event in eventsMkts.items():
        if b_mid in event['markets'].keys():
            e_market = event['markets'][b_mid]
            for runner in bookRes['runners']:
                sid = str(runner['selectionId'])
                # So far runnders sid contains runner name only
                e_market['runners'][sid]['availableToLay'] = runner['ex']['availableToLay']


# =============SANITY CHECKS
log.info('*'*100)
log.info('::SANITY CHECKS::')
log.info('We have: \033[33m %i events in list \033[0m' % len(eventsMkts))
log.info('We have book results for: %i markets \033[33m' % len(marketBookResList))
log.info('There were \033[33m %i Ids with no comp data \033[0m' % len(nocompdataIds))
# Finally, write out results to file
# json.dump(good_eventsList, fp=open('../JSONdata/Betfair.MatchOdds.xjson', 'w'), indent=4)

# Instead of json dump, I will use pymongo to write to mongo
# But let's clean up schema first (get rid of keying)
eventsMktsList = list(eventsMkts.values())
for event in eventsMktsList:
    event['markets'] = event['markets'].values()
    for market in event['markets']:
        market['runners'] = market['runners'].values()

# Clear old and insert
xevents.remove({'exchangeName': 'Betfair'})
xevents_ids = xevents.insert(eventsMktsList)
log.info('Inserted %i entries' % len(xevents_ids))

# timing
print 'Finishing forage at: \033[33m', datetime.datetime.now().strftime('%H:%M:%S'), '\033[0m'
# #############################################################################

# ########Finally logout##########################################################################################
logoutAPI(headers)
