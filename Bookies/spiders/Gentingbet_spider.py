from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
from datetime import datetime as pydt
import json
take_first = TakeFirst()


class GentingbetSpider(Spider):

    name = "Gentingbet"
    allowed_domains = ["gentingcasino.com"]

    # Visit to set session cookie
    def start_requests(self):
        yield Request(url='https://www.gentingcasino.com/sports',
                      callback=self.request_links
                      )

    # Simulate GET requests to server for soccer league list
    def request_links(self, response):
        yield Request(url='https://sports.gentingcasino.com/sportsbook/SOCCER/',
                      callback=self.parse_leagues
                      )

    # First get the league links
    def parse_leagues(self, response):

        league_links = response.xpath('//ul[@class="nav-left nav nav-list"]/ul[@id="subcat-level1"]/li/a/@href').extract()
        league_links = [link for link in league_links if 'EU_CL' not in link]

        base_url = 'https://sports.gentingcasino.com'
        headers = {'Host': 'sports.gentingcasino.com',
                   'Referer': response.url}
        for link in league_links:
            yield Request(url=base_url+link, headers=headers, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        all_scripts = response.xpath('//script')
        wanted_script = take_first([script for script in all_scripts if 'Sportsbook.AppView(' in script.extract()])

        # Manipulate into valid JSON format (attributes quoted etc), then load the string to JSON
        # Get rid of the 'ems: {' as this bracket only closes a few lines down, then drop the final comma too
        jsonEventsData = json.loads(wanted_script.extract().splitlines()[16].lstrip()[4:-1])
        eventSelection = jsonEventsData['events']
        headers = {'Host': 'sports.gentingcasino.com',
                   'Referer': response.url,
                   }
        for event in eventSelection:
            eventId = event['id']
            cref = event['cref']
            scref = event['scref']
            base_url = ('https://sports.gentingcasino.com/sportsbook/%s/%s/%s/'
                        % (cref, scref, eventId))
            yield Request(url=base_url, headers=headers, callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        all_scripts = response.xpath('//script')
        wanted_script = take_first([script for script in all_scripts
                                    if 'Sportsbook.AppView(' in script.extract()])

        jsonEventsData = json.loads(wanted_script.extract().splitlines()[16].lstrip()[4:-1])
        eventSelection = take_first(jsonEventsData['events'])
        marketSelection = take_first(jsonEventsData['markets'].values())
        runnerSelection = jsonEventsData['selections']

        dateTime = eventSelection['s']
        # ms since epoch to s (floor div is fine)
        dateTime = dateTime/1000
        dateTime = pydt.fromtimestamp(dateTime).strftime('%m %d')
        l.add_value('dateTime', dateTime)

        eventName = eventSelection['n']
        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # Markets
        allmktdicts = []
        for mkt in marketSelection:
            marketName = mkt['n']
            marketId = mkt['id']
            mdict = {'marketName': marketName, 'runners': []}
            runners = runnerSelection[str(marketId)]
            for runner in runners:
                try:
                    runnername = runner['n']
                except KeyError:
                    # player to score markets (I think you would need the names
                    # data, i.e. jsonEventsData['names'], then match on ids again
                    continue
                price = runner['ps'][0]['v']
                if runnername and price:
                    mdict['runners'].append({'runnerName': runnername, 'price': price})
            allmktdicts.append(mdict)

        # Do some Gentingbet specific post processing and formating
        for mkt in allmktdicts:
            if 'Match Result' == mkt['marketName']:
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0] in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1] in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'Draw' in runner['runnerName']:
                        runner['runnerName'] = 'DRAW'
            elif 'Correct Score' in mkt['marketName']:
                for runner in mkt['runners']:
                    if teams[1] in runner['runnerName'].lower():
                        runner['reverse_tag'] = True
                    else:
                        runner['reverse_tag'] = False
        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
