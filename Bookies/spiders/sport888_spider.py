from __future__ import division
from scrapy.spider import Spider
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
import json
take_first = TakeFirst()

#
# Just like unibet, 32red, paf, iveriabet, 888 uses Kambi api.
# No point scraping all, just do 888 (see https://kambi.com/contact/)
# Page load loads 'Kambi betting client'
# , which is a swf. But we can still replicate
# its requests to API to get the raw JSON data.
#


class sport888Spider(Spider):
    name = "sport888"
    allowed_domains = ["888sport.com", "kambi.com"]

    # Incase cookie is needed
    start_urls = ['http://www.888sport.com/football/football-betting.htm']

    # First make the leagues request to kambi API
    def parse(self, response):
        # API can vary between api, e-api,e1-api, e2-api, but only api seems to work.

        base_url = 'https://api.kambi.com/offering/api/v2/888/group.json'
        headers = {'Host': 'api.kambi.com',
                   'Referer': 'https://c3-static.kambi.com/sb-bettingclient/client/888/1.67.0.1/bettingclient-shell.swf'}
        GETstr = '?depth=4&lang=en_GB&market=GB&suppress_response_codes&channel_id=1'
        yield Request(url=base_url+GETstr, headers=headers, callback=self.parse_leagues)

    def parse_leagues(self, response):

        jResp = json.loads(response.body)
        groups = jResp['group']['groups']
        football = None
        for g in groups:
            if g['name'] == 'Football':
                football = g

        # Build list of country Ids, needed to call API.
        IdsList = []
        for country in football['groups']:
            IdsList.append(country['id'])

        GETstr = ('cat=1295&market=GB&lang=en_GB&range_size=100&range_start=0&'
                  'suppress_response_codes&channel_id=1')
        headers = {'Referer': 'https://c3-static.kambi.com/sb-bettingclient/client/888/1.67.0.3/bettingclient-shell.swf'}
        unwanted = ['1000094254', ]  # Unwanted ids
        for id in IdsList:
            if id not in unwanted:
                base_url = 'https://api.kambi.com/offering/api/v2/888/betoffer/group/'+str(id)+'.json?'
                yield Request(url=base_url+GETstr, headers=headers, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        jResp = json.loads(response.body)
        jsonEventsData = []
        try:
            jsonEventsData = jResp['events']
            # jsonOddsData = jResp['betoffers']
        except KeyError as e:
            log.msg(e, level=log.ERROR)
            log.msg('Error response or 404? ', level=log.ERROR)
            log.msg('Response dump: \n %s' % jResp)

        for jsonEvent in jsonEventsData:
            boUri = jsonEvent['boUri']
            # Make request for more bets
            base_url = 'https://api.kambi.com'+boUri
            GETstr = '?tmp=&lang=en_GB&market=GB&suppress_response_codes&channel_id=1'
            headers = {'Host': 'api.kambi.com',
                       'Referer': 'https://c3-static.kambi.com/sb-bettingclient/client/888/1.67.0.1/bettingclient-shell.swf'
                       }
            yield Request(url=base_url+GETstr, headers=headers, dont_filter=True,
                          callback=self.parseData)

    def parseData(self, response):

        jResp = json.loads(response.body)

        try:
            jsonEventsData = take_first(jResp['events'])
            jsonOddsData = jResp['betoffers']
        except KeyError as e:
            log.msg(e, level=log.ERROR)
            log.msg('Error response or 404? ', level=log.ERROR)
            log.msg('Response dump: \n %s' % jResp)
            return []
        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = jsonEventsData['start']
        l.add_value('dateTime', dateTime)

        teams = [jsonEventsData['homeName'], jsonEventsData['awayName']]
        l.add_value('teams', teams)

        # Markets
        allmktdicts = []
        for mkt in jsonOddsData:
            marketName = mkt['criterion']['label']
            mdict = {'marketName': marketName, 'runners': []}
            if 'outcomes' in mkt.keys():
                runners = mkt['outcomes']
                for runner in runners:
                    runnerName = runner['label']
                    if 'line' in runner.keys():
                        # For some reason the over/under markets like 10.5
                        # formatted as 1050 in line field.
                        runnerName += ' %.1f' % (runner['line']/1000)
                    price = runner['oddsFractional']
                    mdict['runners'].append({'runnerName': runnerName, 'price': price})
                allmktdicts.append(mdict)

        # Do some 888 specific post processing and formating
        for mkt in allmktdicts:
            if 'Full Time' == mkt['marketName']:
                mkt['marketName'] = 'Match Odds'
            for runner in mkt['runners']:
                if runner['runnerName'] == u'1':
                    runner['runnerName'] = 'HOME'
                elif runner['runnerName'] == u'2':
                    runner['runnerName'] = 'AWAY'
                elif runner['runnerName'] == u'X':
                    runner['runnerName'] = 'DRAW'

        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
