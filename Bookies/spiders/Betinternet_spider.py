from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


class BetinternetSpider(Spider):
    '''
    Scrape mobile site for ease.
    Don't forget to set setting for MOBILE
    user agent string in settings.py to grab
    a mobile ua for this spider.
    '''

    name = "Betinternet"
    allowed_domains = ["betinternet.com"]

    # Visit the homepage first
    def start_requests(self):
        yield Request(url='http://mobile.betinternet.com/en/Sports.bet?method=bycat&catID=51502',
                      callback=self.parse_countries, dont_filter=True)

    def parse_countries(self, response):

        # Only the links from a ul parallel to Football
        countries = response.xpath('//ul[@id="catLinks"]/li/a[text()="Football"]/../ul/li')

        base_url = 'http://mobile.betinternet.com/en/'
        headers = {'Host': 'mobile.betinternet.com',
                   'Referer': response.url,
                   }
        for country in countries:
            countryName = take_first(country.xpath('a/text()').extract())
            countryLink = take_first(country.xpath('a/@href').extract())
            # print countryId, countryName
            leagues = country.xpath('ul/li')
            if leagues and 'Outright' not in countryName:
                for league in leagues:
                    # Make request for each league in leagues
                    # leagueName = take_first(league.xpath('a/text()').extract())
                    leagueLink = take_first(league.xpath('a/@href').extract())
                    # print '--->', leagueId, leagueName
                    yield Request(url=base_url+leagueLink, headers=headers,
                                  dont_filter=True, callback=self.pre_parseData)
            else:
                # No leagues make request for country
                yield Request(url=base_url+countryLink, headers=headers,
                              dont_filter=True, callback=self.pre_parseData)

    def pre_parseData(self, response):

        base_url = 'http://mobile.betinternet.com/en/'
        headers = {'Host': 'mobile.betinternet.com',
                   'Referer': response.url,
                   }
        eventLinks = response.xpath('//ul[@id="events"]/li/a/@href').extract()
        for eventLink in eventLinks:
            yield Request(url=base_url+eventLink, headers=headers,
                          dont_filter=True, callback=self.parseData)

    def parseData(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//div[@class="eventSubHeader"]/'
                                             'span/script/text()').extract())
        dateTime = dateTime[dateTime.find('\"')+1: dateTime.find('\")')]
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[@id="contentHeader"]/'
                                              'h3/text()').extract())
        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # Markets
        mkts = response.xpath('//div[starts-with(@id, "mk_")]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('ul/li/a/text()').extract())
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt.xpath('ul/li/ul/li/div[@class="fOutcome"]')
            for runner in runners:
                runnername = take_first(runner.xpath('div[@class="outName"]/text()').extract())
                price = take_first(runner.xpath('div[@class="outBet"]/a/text()').extract())
                mdict['runners'].append({'runnerName': runnername, 'price': price})
            allmktdicts.append(mdict)

        # Do some Betinternet specific post processing and formating
        for mkt in allmktdicts:
            if '90 mins' in mkt['marketName']:
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
