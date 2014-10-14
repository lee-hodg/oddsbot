#!/usr/bin/env python
from bet_face import loginAPI, logoutAPI, getEventTypes, listMarketBook
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
xmarkets = db.xmarkets  # then exchange_events collection


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
try:
    username = os.environ.get('betfair_username')
    password = os.environ.get('betfair_password')
except KeyError:
    log.error('Betfair username and password should be set as env vars.')
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


# ======================= EVENT LISTING INFO
# List number of events that match filter,
# NB. football has eventTypeID 1. Use
# printEventTypeID(..) with result of getEventTypes(..)
# (with no filter) to get all eventTypeIDs

# efilter = '{"eventTypeIds":["1"], "marketTypeCodes":["MATCH_ODDS"]}'
efilter = {'eventTypeIds': ['1', ]}
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

# =============== MarketCatalogue
# Get marketCatalogue.
# Returns a JSON object with results of
# the marketId, date, name of matching events
#
# Often there are >1000 market Ids to be gotten
# and thus we need to get around the 1000 maxRes limit.
# Use from date filter to do so: grab up to 1000,
# sorted by `FIRST_TO_START`, grab the `openDate` of the last
# event and use as `fromDate` for grabbing the next batch
# of up to 1000, and so on recursively until results is []
#
# This is why we need to append marketCatalogues to list
# (even though marketCatalogue itself is list of results.
marketCatalogueList = []
# ListofLists = []


def grabber(fromDate):

    log.info('Grabbing markets from date %s' % fromDate)
    cnt = raw_input('e2c')
    # Grab up to 1000 from the `fromDate` onwards
    # Remove the MATCH_ODDS type code to get events which have other markets
    # too ready for later
    marketCatalogueFilter = {"eventTypeIds": ["1"],
                             # "marketTypeCodes": ["MATCH_ODDS"],
                             "marketStartTime": {"from": fromDate}
                             }

    maxRes = MAX_RES
    projection = ["EVENT", "COMPETITION", "RUNNER_DESCRIPTION"]
    marketCatalogue = listMarketCatalogue(url, headers,
                                          marketCatalogueFilter,
                                          maxRes,
                                          projection,
                                          sort='FIRST_TO_START')

    if marketCatalogue != -1:
        if marketCatalogue['result']:
            # ms = [(m['marketId'], m['event']['openDate']) for m in marketCatalogue['result']]
            # ListofLists.append(ms)
            marketCatalogueList.append(marketCatalogue)

            # Paging with fromDate and date sorting is somewhat problematic
            # It seems that out-of-the-box it will give duplicates
            # Basically if the 1000th event of batch one finished with
            # date u'2014-10-05T10:30:00.000Z' then this becomes fromDate.
            # Now on the next poll all events that have this date EXACTLY
            # will also be included in the second batch (use the pickle
            # and listoflists to verify with `l[2].index(l[1][-29])` etc.)
            # You can see start of batch 1 is beginning of batch 2 with
            # same datetimes as fromDate.
            # Adding a 1 second delta to fromDate is not a good idea because
            # when cutting off at the 1000th, there still may genuinely be some
            # events with the same datetime that you've not yet included.
            # I think duplication filtering is only way, or use listEvent
            # to get all the events, then in turn grab markets for each using
            # eventid but this could be slow.
            # The extreme case issue (which could and does occur) is if
            # from a certain datetime, e.g. u'2014-10-11T14:00:00.000Z' there
            # are 1000 or more events with exactly the same datetime (saturday
            # aft)
            # this puts the grabber in an infinite loop :(.
            fromDate = marketCatalogue['result'][-1]['event']['openDate']
            # Convert str to datetime obj to add the delta then back to str
            # fromDate = datetime.datetime.strptime(fromDate, '%Y-%m-%dT%H:%M:%S.%fZ')
            # fromDate = fromDate - datetime.timedelta(seconds=(60*3))
            # fromDate = fromDate.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            grabber(fromDate)
    else:
        log.error('listMarketCatalogue returned error -1. Logout. Exit.')
        logoutAPI(headers)
        exit()

# Want only present and future events.
now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
grabber(now)
log.info('Number of marketCatalogues in list  %i' % len(marketCatalogueList))
# import pickle
# pickle.dump(ListofLists, open('dumpfile.p', 'w'))


# Merge JSON from these separate calls
marketCatalogue = {'result': []}
if marketCatalogueList:
    try:
        for mcat in marketCatalogueList:
            check_ids = [resN['marketId'] for resN in mcat['result']]
            log.info('In batch, total num Ids: %i, distinct Ids: %i' %
                     (len(check_ids), len(set(check_ids)))
                     )
            marketCatalogue['result'].extend(mcat['result'])
    except KeyError:
        log.error('KeyError when merging JSON of market catalogue result. Logout. Exit')
        logoutAPI(headers)
        exit()
else:
    log.error('marketCatalogueList empty. Logout. Exit.')
    logoutAPI(headers)
    exit()

marketCatalogueResults = marketCatalogue['result']
log.info('Number of results in merged marketCatalogue is %i' % len(marketCatalogueResults))

# For reasons unknown to me, this still produces some overlapping markets
check_ids = [resN['marketId'] for resN in marketCatalogueResults]
log.info('After merge, total num of market Ids: %i, %i are distinct.'
         % (len(check_ids), len(set(check_ids))))

# ============ Remove duplicate markets
# (maintain order just incase)
from collections import OrderedDict
already_seen = OrderedDict()
for resN in marketCatalogueResults:
    mid = resN['marketId']
    if mid not in already_seen:
        already_seen[mid] = resN
marketCatalogueResults = already_seen.values()

check_ids = [resN['marketId'] for resN in marketCatalogueResults]
log.info('After clean up, total num of market Ids: %i, %i are distinct.'
         % (len(check_ids), len(set(check_ids))))


# ============= GET PRICES DATA

#
# It is vastly faster to get price data
# for a batch of market Ids at once than
# linearly, but too many in a request
# will trigger `TOOMUCHDATA error`; 30 seems
# good.
#
# Sometimes for a given marketId we get no result
# after calling listMarketBook, even if we call
# individually the Id that failed(even with
# non-delayed appKey). We need to
# thus remove these badIds from events list
#
# e.g.marketBooksJSON = bet_face.listMarketBook(url, headers, u'1.113203620')
# '{\n    "jsonrpc": "2.0", \n    "result": [], \n    "id": 1\n}'
# Despite then: marketCatalogueFilter2='{"marketIds":["1.113203620"]}'
# res = bet_face.listMarketCatalogue(url, headers, filter=marketCatalogueFilter2,
#        maxRes='"maxResults":"1"')
# returning seemingly fine listing.
#
# We needed to call `listMarketCatalogue` to get eventName, dateTime, runner
# names etc, so we call `listMarketBook` for the price and stake data, and
# we stitch it all back together using the marketId and selectionId.

log.info('Starting forage at: %s' % datetime.datetime.now().strftime('%H:%M:%S'))

# Build marketIdList, and a few fields of each event in eventsList
# We continue to construct events list dictionaries later when we grab
# the price data.
marketIdList = []  # list of market Ids
eventsList = []
nocompdataIds = []
for resN in marketCatalogueResults:
    try:
        marketId = resN['marketId']
        marketIdList.append(marketId)

        eventDic = {'exchangeName': 'Betfair',
                    'marketId': marketId,
                    'eventName': resN['event']['name'],
                    'dateTime': resN['event']['openDate']
                    }
        # Add shortDateTime too for easier comparison with bookie
        try:
            openDate = datetime.datetime.strptime(resN['event']['openDate'],
                                                  '%Y-%m-%dT%H:%M:%S.%fZ')
            shortDateTime = openDate.strftime('%m %d')
            eventDic['shortDateTime'] = shortDateTime
        except ValueError as e:
            log.error(e)
            eventDic['shortDateTime'] = ''

        try:
            eventDic['team1'], eventDic['team2'] = resN['event']['name'].split(' v ')
        except ValueError:
            eventDic['team1'] = ''
            eventDic['team2'] = ''

        try:
            eventDic['compName'] = resN['competition']['name']
        except KeyError:
            eventDic['compName'] = ''
            # log.error('There was no competition name for event with marketId %s'
            #           % resN['marketId'])
            nocompdataIds.append(marketId)  # debug only
        try:
            eventDic['totalMatched'] = str(resN['totalMatched'])
        except KeyError:
            eventDic['totalMatched'] = ''
        try:
            eventDic['marketName'] = resN['marketName']
        except KeyError:
            eventDic['marketName'] = ''

        # Runner names and selectionIds
        # Index runners by selectionId (needed to match the runnerName to price
        # data later, especially in complicated markets)
        eventDic['runners'] = {}
        MOnames = ['HOME', 'DRAW', 'AWAY']  # translate match odds runner names.
        resRunners = resN['runners']
        if resN['marketName'] == 'Match Odds':
            # Instead of using team names and 'The Draw'
            # use Home Draw Away.
            for posn, runner in enumerate(resRunners):
                sid = str(runner['selectionId'])
                try:
                    eventDic['runners'][sid] = {'runnerName': MOnames[posn],
                                                }
                except IndexError:
                    log.error('IndexError. Exchanging runnerNames to home, away'
                              ' draw. Are there 3 runners? Logout Exit')
                    logoutAPI(headers)
                    exit()
        else:
            for runner in resN['runners']:
                sid = str(runner['selectionId'])
                eventDic['runners'][sid] = {'runnerName': runner['runnerName'],
                                            }
        eventsList.append(eventDic)

    except KeyError as e:
        log.error('KeyError for resN: %s. Logout. Exit.' % e)
        logoutAPI(headers)
        exit()


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
for event in eventsList:
    for bookRes in marketBookResList:
        if event['marketId'] == bookRes['marketId']:
            for runner in bookRes['runners']:
                sid = str(runner['selectionId'])
                # So far runnders sid contains runner name only
                event['runners'][sid]['availableToLay'] = runner['ex']['availableToLay']


# Remove 'bad ids', that returned "result": [] when
# requested with listMarketBook(..) (and thus have no odds data)
eventListIds = [event['marketId'] for event in eventsList]
markbookResIds = [resN['marketId'] for resN in marketBookResList]
badIds = [id for id in eventListIds if id not in markbookResIds]
good_eventsList = [event for event in eventsList if event['marketId'] not in badIds]


# =============SANITY CHECKS
log.info('*'*100)
log.info('::SANITY CHECKS::')
log.info('We have: \033[33m %i events in list \033[0m' % len(eventsList))
log.info('Num of market Ids in list: \033[33m %i  \033[0m' % len(marketIdList))
log.info('We have book results for: %i markets \033[33m' % len(marketBookResList))
log.info('We have: \033[33m %i bad Ids \033[0m' % len(badIds))
log.info('We have: \033[33m %i good events in list aft rem badId events \033[0m'
         % len(good_eventsList))
log.info('List of badIds: %s' % badIds)
log.info('There were \033[33m %i Ids with no comp data \033[0m' % len(nocompdataIds))
# Finally, write out results to file
# json.dump(good_eventsList, fp=open('../JSONdata/Betfair.MatchOdds.xjson', 'w'), indent=4)

# Instead of json dump, I will use pymongo to write to mongo
xmarket_ids = xmarkets.insert(good_eventsList)

# timing
print 'Finishing forage at: \033[33m', datetime.datetime.now().strftime('%H:%M:%S'), '\033[0m'
# #############################################################################

# ########Finally logout##########################################################################################
logoutAPI(headers)
