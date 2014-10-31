from scrapy.spider import Spider
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
import json
import re
take_first = TakeFirst()


class Bet3000Spider(Spider):
    name = "Bet3000"
    allowed_domains = ["bet3000.com"]

    # Visit home, set session cookie, get league JSON
    def start_requests(self):
        yield Request(url='https://www.bet3000.com/en/html/home.html',
                      callback=self.parse_countries
                      )

    def parse_countries(self, response):
        # Get script with country JSON
        all_scripts = response.xpath('//script')
        wanted_script = take_first([script for script in all_scripts if
                                    'Model.CategoryTree.getInstance().load' in script.extract()])

        if not wanted_script:
            log.msg('The js script needed to parse country data was not found. Exit.')
            exit()

        # Manipulate into valid JSON format (attributes quoted etc), then load
        # the string to JSON. Get rid of the 'ems: {' as this bracket only
        # closes a few lines down, then drop the final comma too
        # Everything inside 'Model.CategoryTree.getInstance().load(.....);
        # should be valid JSON, so get with regex
        # (we add the .*}.*document, to avoid matching up to very last );
        _re = re.compile(r'Model\.CategoryTree\.getInstance\(\)\.load\((.*)\);.*}.*document', re.DOTALL)
        x = take_first(wanted_script.re(_re))
        jsonCompData = json.loads(x)

        # Get football country ids
        country_ids = []
        for child in jsonCompData[0]['children']:
            country_ids.append(child['data']['id'])

        # Now for each country_id we need to make the request for event data
        base_url = 'https://www.bet3000.com/en/eventservice/v1/events?'
        headers = {'Referer': 'https://www.bet3000.com/en/html/home.html',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Host': 'www.bet3000.com'}
        unwanted = ['7067', '4328']
        for id in country_ids:
            if str(id) not in unwanted:
                GETstr = 'category_id='+str(id)+'&offset=&live=&sportsbook_id=0'
                url = base_url+GETstr
                yield Request(url=url, headers=headers, callback=self.parse_leagues)

    def parse_leagues(self, response):

        jResp = json.loads(response.body)

        leagueIds = jResp['categories'].keys()
        base_url = 'https://www.bet3000.com/en/eventservice/v1/events'
        headers = {'Host': 'www.bet3000.com',
                   'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Referer': 'https://www.bet3000.com/en/html/home.html'}
        for leagueId in leagueIds:
            GETstr = '?category_id=%s&offset=&live=&sportsbook_id=0' % str(leagueId)
            yield Request(url=base_url+GETstr, headers=headers, callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Parsing data for url %s' % response.url, level=log.INFO)

        # Response body is JSON
        jsonResp = json.loads(response.body)

        try:
            # Event keys
            jsonEvents = jsonResp['events']
            # Market keys (this is an intermediary between event date and actual prices)
            jsonMarkets = jsonResp['markets']
            # Prediction keys
            jsonPredictions = jsonResp['predictions']
        except KeyError as e:
            log.msg(e, level=log.ERROR)
            log.msg('Error response or 404?', level=log.ERROR)
            log.msg('Response dump: %s' % jsonResp)
            return []

        items = []
        for eventKey, event in jsonEvents.items():

            l = EventLoader(item=EventItem2(), response=response)
            l.add_value('sport', u'Football')
            l.add_value('bookie', self.name)

            eventName = event['label']
            if eventName:
                teams = eventName.lower().split(' - ')
                l.add_value('teams', teams)

            dateTime = event['date']
            l.add_value('dateTime', dateTime)

            allmktDics = []
            mktIds = event['markets']
            for mktId in mktIds:
                mkt = jsonMarkets[mktId]
                marketName = mkt['label']
                if mkt['special_value']:
                    marketName += ' ' + mkt['special_value']
                mDict = {'marketName': marketName, 'runners': []}
                runnerIds = mkt['predictions']
                for runnerId in runnerIds:
                    runner = jsonPredictions[runnerId]
                    runnerName = runner['label']
                    price = runner['odds']
                    mDict['runners'].append({'runnerName': runnerName, 'price': price})
                allmktDics.append(mDict)

            # Do some Bet3000 specific post processing and formating
            for mkt in allmktDics:
                if '3-Way' == mkt['marketName']:
                    mkt['marketName'] = 'Match Odds'
                    for runner in mkt['runners']:
                        if teams[0] in runner['runnerName'].lower():
                            runner['runnerName'] = 'HOME'
                        elif teams[1] in runner['runnerName'].lower():
                            runner['runnerName'] = 'AWAY'
                        elif 'The draw' in runner['runnerName']:
                            runner['runnerName'] = 'DRAW'
            # Add markets
            l.add_value('markets', allmktDics)

            # Add and Load item
            items.append(l.load_item())
        return items
