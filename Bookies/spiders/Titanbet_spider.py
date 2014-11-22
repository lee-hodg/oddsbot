from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


# UK only, need VPN
class TitanbetSpider(Spider):
    name = "Titanbet"
    allowed_domains = ["titanbet.com"]
    start_urls = ['http://sports.titanbet.com/en/football']

    # First get the league links
    def parse(self, response):
        league_links = response.xpath('//ul[@class="hierarchy"]/'
                                      'li[@class="expander expander-collapsed sport-FOOT"]/'
                                      'ul[@class="expander-content"]/'
                                      'li[@class="expander expander-collapsed"]/'
                                      'ul[@class="expander-content"]/li/a/@href').extract()
        league_links = [l for l in league_links if not linkFilter(self.name, l)]
        headers = {'Referer': 'http://sports.titanbet.co.uk/en/football',
                   'Host': 'sports.titanbet.co.uk',
                   }
        for link in league_links:
            link = 'http://sports.titanbet.com'+link
            yield Request(link, headers=headers, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        moreLinks = response.xpath('//tr[starts-with(@class, "mkt mkt_content mkt-")]/'
                                   'td[@class="mkt-count"]/a/@href').extract()
        headers = {'Referer': response.url,
                   'Host': 'sports.titanbet.co.uk',
                   }
        for link in moreLinks:
            link = 'http://sports.titanbet.com'+link
            yield Request(link, headers=headers, callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//div[@class="stats-time"]/'
                                             'span[@class="time"]/text()').extract())
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[starts-with(@class, "title ev ev-")]/'
                                              'span/text()').extract())
        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # Markets (only from main area)
        mkts = response.xpath('//div[@id="main-area"]//div[starts-with(@class, "expander") and @data-mkt_id]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('h6/span[@class="mkt-name"]/text()').extract())
            if not marketName:
                # Some are not in span
                marketName = take_first(mkt.xpath('h6/text()').extract()).strip()
            mdict = {'marketName': marketName, 'runners': []}
            # N.B. The collapsed markets need seperate AJAX requests to grab data
            # so far now just forget about them (Also sometimes the mkts, e.g. asians
            # are ul/li instead of tables).
            runners = mkt.xpath('div[@class="expander-content"]/table/'
                                'tbody/tr[@class="limited-row"]/td[starts-with(@class, "seln")]')
            if not runners:
                # Sometimes tr has no class
                runners = mkt.xpath('div[@class="expander-content"]/table/'
                                    'tbody/tr/td[starts-with(@class, "seln")]')
            for runner in runners:
                runnername = take_first(runner.xpath('.//span[@class="seln-name"]/span/text()').extract())
                if not runnername:
                    # E.g. for Correct Score
                    runnername = take_first(runner.xpath('.//span[@class="seln-sort"]/span/text()').extract())
                price = take_first(runner.xpath('.//span[@class="price dec"]/text()').extract())
                mdict['runners'].append({'runnerName': runnername, 'price': price})
            allmktdicts.append(mdict)

        # Do some Titanbet specific post processing and formating
        for mkt in allmktdicts:
            if 'Full Time Result' == mkt['marketName']:
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0] in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1] in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'X' == runner['runnerName']:
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
