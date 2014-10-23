from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


class SkybetSpider(Spider):

    name = "Skybet"
    allowed_domains = ["skybet.com"]

    # Visit the football homepage first for cookies.
    def start_requests(self):
        yield Request(url='http://www.skybet.com/football',
                      callback=self.parse_leagues
                      )

    def parse_leagues(self, response):

        # Get competitions section
        sections = response.xpath('//div[@class="section"]')
        for sec in sections:
            if sec.xpath('h3[@class="hecto"]/text()').extract() == [u'Competitions']:
                compSec = sec

        leagues = compSec.xpath('ul[@class="limit-list"]//li/a/@href').extract()

        # Filter.
        leagues = [league for league in leagues if not linkFilter(self.name, league)]

        # Request leagues.
        base_url = 'http://www.skybet.com'
        headers = {'Referer': 'http://www.skybet.com/football'}
        for league in leagues:
            yield Request(url=base_url+league, headers=headers, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        moreLinks = response.xpath('//div[@class="market-wdw"]/'
                                   'table[@class="mkt mkt11 six-col"]'
                                   '/tbody/tr/td[@class="all-bets-cell"]/a/@href').extract()
        base_url = 'http://www.skybet.com'
        headers = {'Host': 'www.skybet.com',
                   'Referer': response.url,
                   }
        for link in moreLinks:
            yield Request(url=base_url+link, headers=headers, callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = response.xpath('//div[@id="content"]/div[@class="content-head"]'
                                  '/h2[@class="event-title sub-head"]/text()').extract()
        dateTime = ''.join([s.strip() for s in dateTime])
        dateTime = dateTime.split('|')[1]
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[@id="content"]/'
                                              'div[@class="content-head"]'
                                              '/h1/text()').extract())
        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # Markets
        mkts = response.xpath('//div[@class="mktgrp mktgrp1"]/div[starts-with(@class, "market")]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('h3/text()').extract())
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt.xpath('table/tbody/tr/td/a')
            for runner in runners:
                runnername = take_first(runner.xpath('span[@class="oc-desc"]/text()').extract())
                price = take_first(runner.xpath('b[@class="odds"]/text()').extract())
                mdict['runners'].append({'runnerName': runnername, 'price': price})
            allmktdicts.append(mdict)

        # Do some Skybet specific post processing and formating
        for mkt in allmktdicts:
            if 'Full Time Result' in mkt['marketName']:
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
