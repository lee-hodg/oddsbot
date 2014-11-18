from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
import time
import json
take_first = TakeFirst()


class WhitebetSpider(Spider):

    name = "Whitebet"

    # Visit the football homepage first
    def start_requests(self):
        yield Request(url='https://www.whitebet.com/en/betting',
                      callback=self.preLeague)

    def preLeague(self, response):

        '''Make req to API for JSON '''

        stamp = str(int(time.time() * 1000))  # ms since unix epoch
        base_url = 'https://sparklesports.tain.com/'
        GETstr = 'server/rest/event-tree/prelive/tree?lang=en&_='+stamp
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Referer': 'https://www.whitebet.com/en/betting'}

        yield Request(url=base_url+GETstr, headers=headers,
                      callback=self.parseLeague, dont_filter=True)

    def parseLeague(self, response):

        # Get JSON resp
        jsonBody = json.loads(response.body)
        # Get football child
        fchild = take_first([child for child in jsonBody['children']
                             if child['name'] == 'Football'])
        countries = []
        leagues = []
        if fchild:
            # Get country children and ids
            for cchild in fchild['children']:
                countries.append((cchild['name'], cchild['id']))
                for lchild in cchild['children']:
                    # Get league children
                    leagues.append((lchild['name'], lchild['id']))
        base_url = 'https://sparklesports.tain.com'
        GETstr = '/server/rest/event-tree/prelive/events'
        GETstr += '/3/%(id)s'
        GETstr += '?lang=en&currency=EUR&nodeId=%(id)s'
        GETstr += '&nodeType=3&'
        GETstr += 'eventMaxCount=75&_=%(stamp)s'
        headers = {'Host': 'sparklesports.tain.com',
                   'Origin': 'https://www.whitebet.com',
                   'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Referer': 'https://www.whitebet.com/en/betting'}
        for (name, id) in leagues:
            stamp = str(int(time.time() * 1000))  # ms since unix epoch
            newGETstr = GETstr % {'id': str(id), 'stamp': stamp}
            yield Request(url=base_url+newGETstr, headers=headers,
                          callback=self.pre_parseData, dont_filter=True)

    def pre_parseData(self, response):

        jsonBody = json.loads(response.body)

        eventSelection = jsonBody['events']

        base_url = 'https://sparklesports.tain.com'
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Host': 'sparklesports.tain.com',
                   'Origin': 'https://www.whitebet.com',
                   'Referer': 'https://www.whitebet.com/en/betting',
                   }
        for event in eventSelection:
            eventId = event['id']
            stamp = str(int(time.time() * 1000))  # ms since unix epoch
            GETstr = ('/server/rest/event-tree/prelive/events/%s?eventId=%s&'
                      'lang=en&currency=EUR&_=%s' % (eventId, eventId, stamp))
            yield Request(url=base_url+GETstr, headers=headers, callback=self.parseData,
                          dont_filter=True)

    def parseData(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        jsonBody = json.loads(response.body)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = jsonBody['startTime']
        l.add_value('dateTime', dateTime)

        eventName = jsonBody['name']
        if eventName:
            teams = eventName.lower().split(' - ')
            if len(teams) != 2:
                teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # Markets
        mkts = jsonBody['children']
        allmktdicts = []
        for mkt in mkts:
            marketName = mkt['name']
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt['children']
            for runner in runners:
                runnername = runner['name']
                price = runner['odds']
                mdict['runners'].append({'runnerName': runnername, 'price': price})
            allmktdicts.append(mdict)

        # Do some Skybet specific post processing and formating
        for mkt in allmktdicts:
            if mkt['marketName'] == '1X2':
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0] in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1] in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'Draw' in runner['runnerName']:
                        runner['runnerName'] = 'DRAW'
        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
