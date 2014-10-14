#
# Module providing functions for interfacing with
# Betfair NG API, using the superior `requests` library.
#
import requests
import json
#
# login to Betfair and get sessionToken
# SSL certs needed for bot login, see
# https://api.developer.betfair.com/services/webapps/docs/display/1smk3cen4v3lu3yomq5qye0ni/Non-Interactive+%28bot%29+login
#

APINGExceptions = {'-32700': 'Invalid JSON was received by the server. An error occurred on the server while parsing the JSON text.',
                   '-32601': 'Method not found',
                   '-32602': 'Problem parsing the parameters, or a mandatory parameter was not found',
                   '-32603': 'Internal JSON-RPC error'
                   }


def loginAPI(payload, headers):

        print '\033[1;4m **ATTEMPTING LOGIN** \033[0m'

        login_url = 'https://identitysso.betfair.com/api/certlogin'

        try:
            resp = requests.post(login_url, data=payload, cert=('BFcerts/client-2048.crt', 'BFcerts/client-2048.key'), headers=headers)
        except requests.exceptions.RequestException as e:
            print '\033[31m\033[7m %s \033[0m' % e
            exit()

        if resp.status_code == 200:
                resp_json = resp.json()
                print '\033[33m LOGGED IN? '+resp_json['loginStatus']+'\033[0m'
                print 'Session Token:', resp_json['sessionToken']
                return resp_json
        else:
                print " \033[33m Could not login. Status not 200. Exiting \033[0m"
                exit()

#
# logout from Betfair
# e.g: headers = {'X-Application': 'arbOracle', 'Accept': 'application/json', 'X-Authentication': token}
#


def logoutAPI(headers):

        logout_url = 'https://identitysso.betfair.com/api/logout'
        try:
            resp = requests.post(logout_url, headers=headers)
        except requests.exceptions.RequestException as e:
            print '\033[31m\033[7m %s \033[0m' % e
            exit()

        if resp.status_code == 200:
                resp_json = resp.json()
                print '\033[33m LOGGED OUT? '+resp_json['status']+'\033[0m'
                print 'Token:', resp_json['token']
        else:
                print "Logout failed. Status not 200. Exit"
                exit()

# Send Betfair API keep-alive req
# e.g headers = {'X-Application': 'arbOracle', 'Accept': 'application/json', 'X-Authentication': token}
#


def keepaliveAPI(headers):

        keepAlive_url = 'https://identitysso.betfair.com/api/keepAlive'

        try:
            resp = requests.post(keepAlive_url, headers=headers)
        except requests.exceptions.RequestException as e:
            print '\033[31m\033[7m %s \033[0m' % e
            exit()

        if resp.status_code == 200:
                resp_json = resp.json()
                print '\033[33m KEPT ALIVE?'+resp_json['status']+'\033[0m'
                print 'Token:', resp_json['token']
        else:
                print "Keep-alive failed. Status not 200. Exit."
                exit()


#
# make a call API-NG
# return -1 if requests error, otherwise
# return json response
#
def callAPING(url, jsonrpc_req, headers):
        try:
            resp = requests.post(url, jsonrpc_req, headers=headers)
            return resp.json()
        except requests.exceptions.RequestException as e:
            print '\033[31m\033[7m Request error in callAPING \033[0m'
            print '\033[31m\033[7m %s \033[0m' % e
            return -1

#
# getEventTypes operation: get count on events that match.
# other useful filters: "marketCountries":["GB"], "marketTypeCodes":["MATCH_ODDS", "HALF_TIME_SCORE"]
# filter is required, but can be empty
# E.g of resp [{u'eventType': {u'id': u'1', u'name': u'Soccer'}, u'marketCount': 840}]
# you can get Ids by first calling this function without filter '{}', and then passing result
# to printEventTypeID below
#


def getEventTypes(url, headers, efilter):

    # build json request header from filter
    event_type_req_dict = {"jsonrpc": "2.0",
                           "method": "SportsAPING/v1.0/listEventTypes",
                           "params": {"filter": efilter,
                                      },
                           "id": 1
                           }

    event_type_req = json.dumps(event_type_req_dict)
    eventTypesJSON = callAPING(url, event_type_req, headers)

    if eventTypesJSON == -1:
        # error with request itself (e.g timeout)
        return -1
    else:
        try:
            # test if ErrorResponse (API replied but there was an issue)
            errorResponse = eventTypesJSON['error']
            print '\033[31m\033[7m %s \033[0m' % errorResponse
            print 'Associated Exception msg:', APINGExceptions[str(errorResponse['code'])]
            return -1
        except KeyError:
            # expected behaviour: no error, return JSON resp
            return eventTypesJSON

#
# Extraction eventypeId for eventTypeName from evetypeResults
# If you make the above getEventTypes call, without filtering (filter='{}') on eventId
# then pass it this function it prints a list of events (football, horses, rugby...)
# against their Ids.
# Mainly a helper function.
#


def printEventTypeID(eventTypesResult):

    eventTypesResult = eventTypesResult['result']

    if eventTypesResult:
        for event in eventTypesResult:
            eventTypeName = event['eventType']['name']
            eventTypeId = event['eventType']['id']
            print 'EventType:', eventTypeName, ': ID:', eventTypeId
    else:
        print '\033[31m\033[7m Oops there is an issue with the input \033[0m'


def listEvents(url, headers, mfilter):

    print 'Calling listEvents endpoint'

    # build request
    events_req_dict = {'jsonrpc': '2.0',
                       'method': 'SportsAPING/v1.0/listEvents',
                       'params': {'filter': mfilter,
                                  },
                       'id': 1,
                       }

    # Now dump str
    events_req = json.dumps(events_req_dict)
    # Make request
    eventsJSON = callAPING(url, events_req, headers)

    if eventsJSON == -1:
        # error with request itself (e.g timeout)
        return -1
    else:
        try:
            # test if ErrorResponse (API replied but there was an issue)
            errorResponse = eventsJSON['error']
            print '\033[31m\033[7m %s \033[0m' % errorResponse
            print 'Associated Exception msg:', APINGExceptions[str(errorResponse['code'])]
            return -1
        except KeyError:
            # this is the expected behaviour: no errorResponse, return JSON resp
            return eventsJSON


#
# marketCatalogue to get marketDetails
# other useful filters "marketCountries":["GB"]
# filter= '{"eventTypeIds":["' + eventTypeID + '"],"marketTypeCodes":["MATCH_ODDS"],'\
#      '"marketStartTime":{"from":"' + now + '"}},"sort":"FIRST_TO_START","maxResults":'+maxRes+',"marketProjection":["EVENT"]}'
# Returns data like
# {
#            "totalMatched": 27.84,
#            "marketName": "Match Odds",
#            "event": {
#                "timezone": "GMT",
#                "openDate": "2014-03-12T23:30:00.000Z",
#                "id": "27164774",
#                "countryCode": "BR",
#                "name": "Marcilio Dias v Brusque"
#            },
#            "marketId": "1.113179066"
# for single id:
# marketCatalogueFilter2 = '{"marketIds":["1.113104170"]}'
# listMarketCatalogure(url, headers, filter=marketCatalogueFilter2, maxRes='"maxResults":"1"')
#
# NB: maxRes is required along with filter
# marketProjection determines what data will be returned
# e.g. league info, event info etc
#
# NB Here tempting to make them lists or dicts defaults for args.
# Classic python error, only init on first
# define of func, then it will be same list each call) and accumulate
def listMarketCatalogue(url, headers, mfilter, maxRes,
                        projection, sort=None):
    print 'Calling listMarketCatalogue Operation to get MarketID and selectionId'

    # build request
    market_catalogue_req_dict = {'jsonrpc': '2.0',
                                 'method': 'SportsAPING/v1.0/listMarketCatalogue',
                                 'params': {'filter': mfilter,
                                            'maxResults': maxRes,
                                            'marketProjection': projection,
                                            },
                                 'id': 1,
                                 }
    if sort:
        market_catalogue_req_dict['params']['sort'] = sort

    # Now dump str
    market_catalogue_req = json.dumps(market_catalogue_req_dict)
    # Make request
    market_catalogueJSON = callAPING(url, market_catalogue_req, headers)

    if market_catalogueJSON == -1:
        # error with request itself (e.g timeout)
        return -1
    else:
        try:
            # test if ErrorResponse (API replied but there was an issue)
            errorResponse = market_catalogueJSON['error']
            print '\033[31m\033[7m %s \033[0m' % errorResponse
            print 'Associated Exception msg:', APINGExceptions[str(errorResponse['code'])]
            return -1
        except KeyError:
            # this is the expected behaviour: no errorResponse, return JSON resp
            # print json.dumps(market_catalogueJSON, indent=4)
            return market_catalogueJSON


#
# Get the book result for one or more marketIds.
# Book res contains prices and stake available amounts
# (the stuff we want!)
# listMarketBook(url, headers, 1.113104314, 1.113104170)
# The exBestOffersOverrides (NB lowercase!) gives depth of 1
#
def listMarketBook(url, headers, price_proj, *marketIds):

    # Build request
    # mID_list_str = '[%s]' % ', '.join(marketIds) #marketIds is a tuple, turn into a list str
    # price_proj = {"priceData": ["EX_BEST_OFFERS"],
    #               "exBestOffersOverrides": {"bestPricesDepth": 3}
    #               }
    market_book_req_dict = {"jsonrpc": "2.0",
                            "method": "SportsAPING/v1.0/listMarketBook",
                            "params": {"marketIds": marketIds,
                                       "priceProjection": price_proj,
                                       },
                            "id": 1
                            }
    # Dump to str
    market_book_req = json.dumps(market_book_req_dict)

    # Make request
    market_bookJSON = callAPING(url, market_book_req, headers)

    if market_bookJSON == -1:
        # error with request itself (e.g timeout)
        return -1
    elif market_bookJSON:  # not empty list
        try:
            # test if ErrorResponse (API replied but there was an issue)
            errorResponse = market_bookJSON['error']
            print '\033[31m\033[7m %s \033[0m' % errorResponse
            print 'Associated Exception msg:', APINGExceptions[str(errorResponse['code'])]
            return -1
        except KeyError:
            # expected behaviour: no error, return JSON resp
            # print json.dumps(market_bookJSON, indent=4)
            return market_bookJSON
