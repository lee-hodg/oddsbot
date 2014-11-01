from __future__ import division
import json
import re
from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
from scrapy.http import FormRequest
from Bookies.help_func import getOddsRounded
take_first = TakeFirst()


def am2dec(odd):
    '''
    Rather than use help_func.am2dec, this
    version uses getOddsRounded and is Setanta specific.
    Convert US odds to Decimal style.
    '''
    if odd in ['EV', 'ev', 'even', 'evens']:
        return odd

    try:
        odd = float(odd)
    except ValueError:
        return -1

    # first round the odds like setantabet do
    odd = getOddsRounded(odd)

    # retrun formatted 2d
    if odd <= -100:
        return "%0.2f" % (1-(100/odd))
    else:
        return "%0.2f" % (1+(odd/100))


# c.f. Heavenbet
class SetantabetSpider(Spider):

    name = "Setantabet"

    allowed_domains = ["setantabet.com", "sbtech.com"]
    # First grab league classes
    url = 'https://www.setantabet.com/en-gb/Sportsbook'
    start_urls = [url]

    def parse(self, response):
        # CurrentCultureCode cookie gets set here
        # Make initial ajax req
        base_url = 'https://setantabet.sbtech.com/'
        headers = {'Referer': 'https://www.setantabet.com/en-gb/Sportsbook'}

        yield Request(url=base_url,
                      headers=headers,
                      callback=self.parseAJAX1)

    def parseAJAX1(self, response):
        '''
        This will set a number of cookies
        ASP.NET_SessionId, firstrequest, lng, firstreferer, cTz, oSt2
        The response itself just consists of the sports menu on LHS and some
        live events.
        '''

        # There are two more reqs after this hshandler and achan. Are they
        # important? or should I just move onto the football league req?
        # I think they are just javascripts being grabbed by other included
        # javascripts (perhaps through jsRequire type funcs UniSlip.js),
        # so more than likely no big deal.
        headers = {'Host': 'setantabet.sbtech.com',
                   'Referer': 'https://setantabet.sbtech.com/'}
        base_url = 'https://setantabet.sbtech.com/football/'

        yield Request(url=base_url,
                      headers=headers,
                      callback=self.preparseLeagues)

    def preparseLeagues(self, response):
        base_url = 'https://setantabet.sbtech.com/pagemethods.aspx/getBranchFilters?branchId=1'
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'Host': 'setantabet.sbtech.com',
                   'Referer': 'https://setantabet.sbtech.com/football/',
                   'RequestTarget': 'AJAXService'
                   }

        yield Request(url=base_url,
                      headers=headers,
                      callback=self.parseLeagues)

    def parseLeagues(self, response):
        # js array (see Heavenbet)
        jsonstr = re.sub(",(?=,)", ",null", response.body)
        jsonBody = json.loads(jsonstr)

        # Get LeaguesCollection Ids first, this json should now
        # contain leagues and ids, plus the markets these leagues offer.
        # child[5] is the markets available, if it is [] it will not be shown
        # on setantabet.com, we should also drop it
        leagues = []
        for child in jsonBody:
            # 0 is id, 1 is name
            lid = child[0]
            lname = child[1]
            markets = child[5]
            if markets:
                leagues.append((lid, lname))

        # POST req
        base_url = 'https://setantabet.sbtech.com/pagemethods.aspx/GetLeaguesContent'
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                   'Host': 'setantabet.sbtech.com',
                   'Pragma': 'no-cache',
                   'Referer': 'https://setantabet.sbtech.com/football/',
                   'RequestTarget': 'AJAXService'}
        for league in leagues:
            data = {'BranchID': '1',
                    'LeaguesCollection': str(league[0])
                    }
            yield FormRequest(url=base_url, formdata=data, headers=headers,
                              callback=self.pre_parseData)

    def pre_parseData(self, response):

        '''
        We have at this stage all the event data
        like eventName and dateTime but not prices
        . It's more efficient to request price data
        for every event at once, and pass event data
        in a dictionary with eventId as key, then rematch
        events to prices in parseData
        '''

        # Once against resp is js array
        # jsonstr = re.sub("[,]{2,}", ",", response.body)
        # Use null insted of collapsing to fill ,,
        # keeps array indices fixed independent of data being there.
        jsonstr = re.sub(",(?=,)", ",null", response.body)
        jsonBody = json.loads(jsonstr)
        eventSelection = jsonBody[0][1]

        metaDict = {'events': {}}
        marketIds = []
        if eventSelection:
            # Sometimes 0 if just outrights.
            for event in eventSelection:
                # event id (n.b. lid is event[3])
                eid = event[0]

                # eventName
                team1 = event[1]
                team2 = event[2]
                teams = [team1, team2]

                # dateTime
                dateTime = event[4]  # 2014-06-25T09:30:00.0000000

                mkts = event[5]
                # MO only (believe second element being zero signifies 1x2
                # you could call other markets too, but decoding is difficult
                # (easy to identify some asian handicap runners and US odds
                # but generally matching to marketName can be tricky)
                # To upgrade in the future we could include all markets here for
                # the event.
                MOmarketId = take_first([str(mkt[0]) for mkt in mkts if mkt[1] == 0])
                eventDict = {'teams': teams, 'dateTime': dateTime,
                             'MOmarketId': MOmarketId}
                metaDict['events'][eid] = eventDict
                if MOmarketId:
                    marketIds.append(MOmarketId)

            base_url = 'https://setantabet.sbtech.com/pagemethods.aspx/UpdateEvents'
            headers = {'RequestTarget': 'AJAXService',
                       'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                       'Referer': 'https://setantabet.sbtech.com/football/'}
            GETstr = "?requestString="
            GETstr += '@'.join(marketIds)
            yield Request(url=base_url+GETstr, headers=headers,
                          callback=self.parseData, meta=metaDict)

    def parseData(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        # Once against resp is js array
        # jsonstr = re.sub("[,]{2,}", ",", response.body)
        jsonstr = re.sub(",(?=,)", ",null", response.body)
        try:
            jsonBody = json.loads(jsonstr)
        except ValueError as e:
            log.msg(e, level=log.ERROR)
            log.msg('jsonstr: %s' % jsonstr)
            return []

        items = []
        for event in response.meta['events'].values():

            l = EventLoader(item=EventItem2(), response=response)
            l.add_value('sport', u'Football')
            l.add_value('bookie', self.name)

            dateTime = event['dateTime']
            l.add_value('dateTime', dateTime)

            teams = event['teams']
            if teams:
                l.add_value('teams', teams)

            # Get odds
            MOdict = {'marketName': 'Match Odds', 'runners': []}
            for mktData in jsonBody:
                marketId = str(mktData[0])
                # To upgrade in future could be marketData[0] in
                # event['marketIds']
                if marketId == event['MOmarketId']:
                    # Is the assumption 1x2 is first always good?
                    oddsData = mktData[2][0][1]  # 1x2 data is first
                    if oddsData:
                        home_price = am2dec(oddsData[1])
                        draw_price = am2dec(oddsData[3])
                        away_price = am2dec(oddsData[5])
                        MOdict['runners'] = [{'runnerName': 'HOME',
                                             'price': home_price},
                                             {'runnerName': 'DRAW',
                                             'price': draw_price},
                                             {'runnerName': 'AWAY',
                                             'price': away_price},
                                             ]

            # Add markets
            l.add_value('markets', [MOdict, ])

            # Load item
            items.append(l.load_item())
        return items
