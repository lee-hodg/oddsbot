from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


class BetclicSpider(Spider):
    name = "Betclic"
    allowed_domains = ["betclic.com"]

    # Visit the football homepage first
    def start_requests(self):
        yield Request(url='https://en.betclic.com/football-s1',
                      callback=self.parse_leagues
                      )

    def parse_leagues(self, response):

        names = response.xpath('//ul[@class="listAllCompet"]/li/a/text()').extract()
        league_links = response.xpath('//ul[@class="listAllCompet"]/li/a/@href').extract()
        # zip
        league_pairs = zip(names, league_links)

        # Remove unwanted links; returns True to filter out link
        league_links = [link for (league_name, link) in league_pairs
                        if not linkFilter(self.name, league_name)]

        base_url = 'https://en.betclic.com'
        headers = {'Referer': 'https://en.betclic.com/calendar/football-s1i1',
                   'Host': 'en.betclic.com'}
        for link in league_links:
            yield Request(url=base_url+link, headers=headers, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        moreLinks = response.xpath('//a[starts-with(@class, "qTip more-odds extra-info")]/@href').extract()

        base_url = 'https://en.betclic.com'
        headers = {'Referer': response.url,
                   'Host': 'en.betclic.com'}
        for link in moreLinks:
            yield Request(url=base_url+link, headers=headers, callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//div[@class="section-header-right"]/'
                                             'time/text()').extract())
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[@class="section-header-left"]/'
                                              'h1/text()').extract())
        if eventName:
            teams = eventName.lower().split(' - ')
            l.add_value('teams', teams)

        # Markets
        mkts = response.xpath('//div[starts-with(@id, "market_marketTypeCode_")]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('div[starts-with(@class, "section-title")]/'
                                              'span[@class="label-market"]/text()').extract())
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt.xpath('div[@class="odds multi"]/table/tbody/tr/td')
            for runner in runners:
                runnername = take_first(runner.xpath('span[@class="odd-label"]/text()').extract())
                price = take_first(runner.xpath('span[@class="odd-button"]/text()').extract())
                if runnername and price:
                    mdict['runners'].append({'runnerName': runnername, 'price': price})
            allmktdicts.append(mdict)

        # Do some Betclic specific post processing and formating
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
        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
