from scrapy.spider import Spider
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
take_first = TakeFirst()


class BGbetSpider(Spider):
    name = "BGbet"
    allowed_domains = ["bgbet.com"]

    # BGbet has url with everything listed (excellent)
    start_urls = ['http://www.bgbet.com/events/football.aspx']

    download_timeout = 120  # BGbet sometimes needs longer than settings timeout

    def parse(self, response):
        log.msg('Grabbing morebet links...', level=log.INFO)
        moreBets = response.xpath('//div[contains(@class, "oddLine") or contains(@class, "evenLine")]'
                                  '/div/span[@class="moreMarkets"]/a/@href').extract()
        base_url = 'http://www.bgbet.com/events/'
        headers = {'Host': 'www.bgbet.com',
                   'Referer': 'http://www.bgbet.com/events/football.aspx'
                   }
        for link in moreBets:
            yield Request(url=base_url+link, headers=headers, callback=self.parseData,
                          dont_filter=True)

    def parseData(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//div[@id="ContentWrapper"]/'
                                             'div[@class="antepostContainer"]/'
                                             'div[@class="antepostMarketContainer"]/'
                                             'div[1][@class="antepostEventContainer"]/'
                                             'h4/span/text()').extract())
        # Sometimes instead of divs we get an entire reponse with same class/ids
        # but using tables/tr/td instead of the divs. We could use element wildcards
        # but I think it might be a bit messy.
        if not dateTime:
            dateTime = take_first(response.xpath('//table[@class="antepostEventContainer"][1]/'
                                                 'tr[1]/td[1]/h4/span/text()').extract())
        dateTime = dateTime.split('-')[1]

        dateTime = dateTime.replace('till', '')
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//h3[@class="antepostHeader"]/text()').extract())

        if eventName:
            teams = eventName.lower().split(' vs ')
            l.add_value('teams', teams)

        # Markets
        mkts = response.xpath('//div[@class="antepostEventContainer"]')
        if not mkts:
            mkts = response.xpath('//table[@class="antepostEventContainer"]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('h4[@class="antepostEventHeader"]/span/text()').extract())
            if not marketName:
                marketName = take_first(mkt.xpath('tr/td/h4[@class="antepostEventHeader"]/span/text()').extract())
            marketName = take_first(marketName.split(' - '))
            mdict = {'marketName': marketName, 'runners': []}
            if 'Correct Score' in marketName:
                runners = mkt.xpath('div[@class="correctScoreContainer"]/'
                                    'div[not(@class="clear")]/div[starts-with(@class, "selection")]')
                if not runners:
                    runners = mkt.xpath('tr/td/table[@class="correctScoreContainer"]/'
                                        'tr/td/table[not(@class="clear")]/'
                                        'tr/td/table[starts-with(@class, "selection")]/tr/td')
                for runner in runners:
                    runnername = take_first(runner.xpath('span[@class="name"]/text()').extract())
                    price = take_first(runner.xpath('span[@class="price"]/text()').extract())
                    mdict['runners'].append({'runnerName': runnername,
                                             'price': price,
                                             })
            else:
                runners = mkt.xpath('div[@class="antepostSelectionContainer"]/'
                                    'div[starts-with(@class, "antepostSelection")]')
                if not runners:
                    runners = mkt.xpath('tr/td/table[@class="antepostSelectionContainer"]/'
                                        'tr/td/table[starts-with(@class, "antepostSelection")]/tr/td')
                for runner in runners:
                    runnerName = take_first(runner.xpath('span[@class="antepostSelectionName"]/text()').extract())
                    price = take_first(runner.xpath('span[@class="antepostSelectionOdds"]/text()').extract())
                    mdict['runners'].append({'runnerName': runnerName, 'price': price})
            allmktdicts.append(mdict)

        # Do some BGbet specific post processing and formating
        for mkt in allmktdicts:
            if 'Ninety Minutes' == mkt['marketName']:
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0] in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1] in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'Draw' in runner['runnerName']:
                        runner['runnerName'] = 'DRAW'
            elif 'Correct Scores' in mkt['marketName']:
                mkt['marketName'] = 'Correct Score'
                for runner in mkt['runners']:
                    if teams[1] in runner['runnerName'].lower():
                        runner['reverse_tag'] = True
                    else:
                        runner['reverse_tag'] = False

        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
