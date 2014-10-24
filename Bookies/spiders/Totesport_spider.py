from scrapy.spider import Spider
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
take_first = TakeFirst()


class TotesportSpider(Spider):
    name = "Totesport"

    start_urls = ['http://www.totesport.com/portal?'
                  'action=GoCategory&category=Football&Sports-Betting-Football']

    # You must retain the name 'parse' with basic spider!
    def parse(self, response):

        league_links = response.xpath('//div[@id="nav"]//ul[@id="sport_menu"]//li/a/@href').extract()
        # Remove some junk competitions
        league_links = [link for link in league_links if ('action=GoRegion' in link)
                        and ('&region_id=10' not in link)]

        # Make GET request
        headers = {'Referer': response.url,
                   'Host': 'www.totesport.com',
                   }
        for link in league_links:
            yield Request(url=link, headers=headers, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):
        events = response.xpath('//div[@class="market_table_wrapper"]/'
                                'table/tbody/tr')
        headers = {'Host': 'www.totesport.com',
                   'Referer': response.url,
                   }
        for event in events:
            # Datetime not on detail page, thus pass via meta
            dateTime = take_first(event.xpath('td[@class="date_time"]/text()').extract())
            link = take_first(event.xpath('td[@class="sel"]/a/@href').extract())
            if link:
                # For outrights this will be None
                yield Request(url=link, headers=headers,
                              meta={'dateTime': dateTime}, callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url, level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = response.meta['dateTime']
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[@class="market_title_top"]/'
                                              'h1/text()').extract())

        if eventName:
            teams = eventName.lower().split(' vs ')
            l.add_value('teams', teams)

        # Markets
        mkts = response.xpath('//div[@class="market_wrapper"]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('div[@class="market_title"]/h2/text()').extract())
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt.xpath('div[@class="market_content_wrapper"]/'
                                'div[@class="market_content"]/table/'
                                'tbody/tr/td[@class="odds"]')
            for runner in runners:
                runnerName = take_first(runner.xpath('a/@title').extract())
                price = take_first(runner.xpath('a/text()').extract())
                if runnerName and price:
                    mdict['runners'].append({'runnerName': runnerName, 'price': price})
            allmktdicts.append(mdict)

        # Do some Totesport specific post processing and formating
        for mkt in allmktdicts:
            if '90 Minutes' == mkt['marketName']:
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0] in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1] in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'Draw' in runner['runnerName']:
                        runner['runnerName'] = 'DRAW'
            elif 'Correct Score' == mkt['marketName']:
                for runner in mkt['runners']:
                    try:
                        if teams[1] in runner['runnerName'].lower():
                            runner['reverse_tag'] = True
                        else:
                            runner['reverse_tag'] = False
                    except AttributeError:
                        print runner
                        continue
        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
