from scrapy.spider import Spider
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
import json
take_first = TakeFirst()

#
# This is the new BuzzOdds spider.
# They now seem to use elecgames external API,
# and rec JSON response from it. NB necessary to visit
# elecgames with a referer BuzzOdds to first set PHPSESSION cookie
#


class BuzzoddsSpider(Spider):

    name = "Buzzodds"
    allowed_domains = ["Buzzodds.com", "elecgames.net"]

    # Incase cookie is needed
    start_urls = ['https://www.buzzpoker.com/buzz-odds']

    # Need to also get elecgames API to set their PHPsession cookie
    def parse(self, response):
        base_url = 'https://sports.elecgames.net'
        GETstr = '/?partner=BuzzPoker&locale=en_GB'
        headers = {'Referer': 'https://www.buzzpoker.com/buzz-odds'}
        yield Request(url=base_url+GETstr, headers=headers, callback=self.pre_parse_countries)

    # Make request for countries data
    def pre_parse_countries(self, response):
        base_url = 'https://sports.elecgames.net/portal/tree/'
        GETstr = '?id=5&isLive=2&startsWithin=0'
        headers = {'Referer': 'https://sports.elecgames.net/?partner=BuzzPoker&locale=en_GB',
                   'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'X-Requested-With': 'XMLHttpRequest'}

        yield Request(url=base_url+GETstr, headers=headers, callback=self.parse_countries)

    def parse_countries(self, response):

        # Extract the needed params from the JSON response
        jResp = json.loads(response.body)
        countries = {}
        unwanted = ['World Cup 2010']
        for c in jResp['response']:
            if c['name'] not in unwanted:
                countries[c['name']] = c['id']

        base_url = 'https://sports.elecgames.net/portal/tree/'
        headers = {'Referer': 'https://sports.elecgames.net/?partner=BuzzPoker&locale=en_GB',
                   'Accept:': 'Accept: application/json, text/javascript, */*; q=0.01',
                   'X-Requested-With': 'XMLHttpRequest'}

        for country in countries.keys():
            GETstr = '?id=%s&isLive=2&startsWithin=0' % countries[country]
            yield Request(url=base_url+GETstr, headers=headers, callback=self.parse_leagues)

    def parse_leagues(self, response):

        # Extract the needed params from the JSON response
        jResp = json.loads(response.body)
        leagues = {}
        for l in jResp['response']:
            leagues[l['name']] = l['BpCompetitionId']

        base_url = 'https://sports.elecgames.net/portal/events/'
        headers = {'Referer': 'https://sports.elecgames.net/?partner=BuzzPoker&locale=en_GB',
                   'Accept:': 'Accept: application/json, text/javascript, */*; q=0.01',
                   'X-Requested-With': 'XMLHttpRequest'}

        for lname, leagueId in leagues.items():
            GETstr = '?id=%s&isLive=2&startsWithin=0' % leagueId
            yield Request(url=base_url+GETstr, headers=headers,
                          meta={'lname': lname}, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        league_name = response.meta['lname']

        jResp = json.loads(response.body)
        jsonEventsData = jResp['response']

        base_url = 'https://sports.elecgames.net/portal/event/'
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Host': 'sports.elecgames.net',
                   'Referer': response.url,
                   'X-Requested-With': 'XMLHttpRequest'
                   }
        # GET BpEventId
        for event in jsonEventsData:
            BpEventId = event['BpEventId']
            isLive = str(event['isLive'])
            GETstr = '?id=%s&isLive=%s' % (BpEventId, isLive)
            yield Request(url=base_url+GETstr, headers=headers,
                          meta={'league_name': league_name, 'BpEventId': BpEventId},
                          callback=self.parse_Data)

    def parse_Data(self, response):

        league_name = response.meta['league_name']
        BpEventId = response.meta['BpEventId']

        log.msg('Parsing data for url %s' % response.url)
        log.msg('Parsing for league %s and event Id %s' % (league_name, BpEventId))
        jResp = json.loads(response.body)
        try:
            jData = jResp['response']
        except (TypeError, KeyError):
            jData = jResp['error']
            log.msg('Error response for %s and event Id %s' % (league_name, BpEventId),
                    level=log.ERROR)
            log.msg('Error response: %s' % jData, level=log.ERROR)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        try:
            dateTime = jData['StartTimeUTC']
            l.add_value('dateTime', dateTime)
        except (TypeError, KeyError):
            log.msg('KeyError jData dump is: %s\n KeyError for %s and event Id %s'
                    % (jData, league_name, BpEventId), level=log.ERROR)
            return []

        eventName = jData['name']
        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # More ambitiously, grab all markets
        # First all unique market names
        mktNames = set()
        for seln in jData['Selections']:
            mktNames.add(seln['MarketName'])
        # Now construct a market dic for each unique market name
        allMktDicts = []
        for mktName in mktNames:
            mDict = {'marketName': mktName, 'runners': []}
            for seln in jData['Selections']:
                if seln['MarketName'] == mktName:
                    runnerName = seln['BettingAlternativeName'].upper()
                    price = seln['Odds']
                    stake = seln['Stake']
                    mDict['runners'].append({'runnerName': runnerName,
                                             'price': price,
                                             'stake': stake,
                                             })
            allMktDicts.append(mDict)

        # Add markets
        l.add_value('markets', allMktDicts)

        # Load item
        return l.load_item()
