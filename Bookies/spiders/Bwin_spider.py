from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


class BwinSpider(Spider):

    name = "Bwin"
    allowed_domains = ["bwin.com"]

    # Visit the football homepage first
    def start_requests(self):
        yield Request(url='https://sports.bwin.com/en/sports/4/betting/football#sportId=4',
                      callback=self.parse_leagues
                      )

    def parse_leagues(self, response):

        # League links from nav and hidden 'more' nav.
        links = response.xpath('//ul[@id="nav-top-list"]/li[@class="nav-toggle"]/ul/li/a/@href').extract()
        links += response.xpath('//ul[@id="nav-more-list"]//li[@class="nav-toggle"]/ul/li/a/@href').extract()

        headers = {'Host': 'sports.bwin.com',
                   'Referer': response.url,
                   'X-Requested-With': 'XMLHttpRequest',
                   }
        base_url = 'https://sports.bwin.com'
        for link in links:
            yield Request(url=base_url+link, headers=headers, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        moreLinks = response.xpath('//div[@id="markets"]//div[@class="more"]/'
                                   'a[not(@class="statistics")]/@href').extract()

        headers = {'Host': 'sports.bwin.com',
                   'Referer': response.url,
                   'X-Requested-With': 'XMLHttpRequest',
                   }
        base_url = 'https://sports.bwin.com'
        for link in moreLinks:
            yield Request(url=base_url+link, headers=headers, callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//div[@id="event-info"]/'
                                             'span[not(@class="more")]/text()').extract())
        dateTime = take_first(dateTime.split(','))
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[@id="event-info"]/'
                                              'h1[@class="league-name"]/text()').extract())
        if eventName:
            teams = eventName.lower().split(' - ')
            l.add_value('teams', teams)

        # Markets
        mkts = response.xpath('//div[starts-with(@id, "game-wrapper-s-")]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('div/h6/text()').extract())
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt.xpath('div/ul/li/table/tr/td/form/button')
            for runner in runners:
                runnername = take_first(runner.xpath('span[@class="option-name"]/text()').extract())
                price = take_first(runner.xpath('span[@class="odds"]/text()').extract())
                mdict['runners'].append({'runnerName': runnername, 'price': price})
            allmktdicts.append(mdict)

        # Do some Bwin specific post processing and formating
        for mkt in allmktdicts:
            if '3-way - result' == mkt['marketName']:
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0].strip() in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1].strip() in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'X' == runner['runnerName']:
                        runner['runnerName'] = 'DRAW'
            elif 'Goal bet (regular time)' == mkt['marketName']:
                mkt['marketName'] = 'Correct Score'

        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
