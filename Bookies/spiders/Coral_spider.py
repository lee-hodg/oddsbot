from scrapy.spider import Spider
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
take_first = TakeFirst()


class CoralSpider(Spider):
    name = "Coral"
    allowed_domains = ["coral.co.uk"]

    # Coral has URL with everything listed (excellent)
    start_urls = ['http://sports.coral.co.uk/football/coupons/all-matches-coupon']

    def parse(self, response):
        log.msg('Grabbing all more bets links before traversing them in turn.')
        links = response.xpath('//div[@class="match featured-match"]/div[@class="go-to-bets"]/a/@href').extract()
        headers = {'Referer': 'http://sports.coral.co.uk/football/coupons/all-matches-coupon',
                   }
        for link in links:
            yield Request(url=link, headers=headers, callback=self.parseEvent)

    def parseEvent(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//div[@class="event-markets"]/div[@class="block-header"]'
                                             '/div[@class="center-col-options"]'
                                             '/div[last()]/text()').extract())

        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[@class="game-all-markets"]/div/'
                                              'div[@class="block-header"]/'
                                              'span[@class="block-title"]/text()').extract())

        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # I think we need to more specifically target markets formatting too diff
        # between them
        markets = response.xpath('//div[@class="market-wrapper"]')

        # Lets get MO
        # N.B. just like a filesystem path we go upward with '..', after
        # we find the ones with Match Result only
        MOmarket = markets.xpath('div[@class="block-header-wrapper"]/div/'
                                 'span[@class="block-title" and text()="Match Result"]/'
                                 '../../../div[@class="matches"]')

        # MO prices
        MOdict = {'marketName': 'Match Odds'}
        home_price = take_first(MOmarket.xpath('table/tr[@class="body-row"]/td[1]//'
                                               'span[@class="odds-fractional"]/text()').extract())

        draw_price = take_first(MOmarket.xpath('table/tr[@class="body-row"]/td[2]//'
                                               'span[@class="odds-fractional"]/text()').extract())

        away_price = take_first(MOmarket.xpath('table/tr[@class="body-row"]/td[3]//'
                                               'span[@class="odds-fractional"]/text()').extract())
        MOdict['runners'] = [{'runnerName': 'HOME',
                             'price': home_price},
                             {'runnerName': 'DRAW',
                              'price': draw_price},
                             {'runnerName': 'AWAY',
                              'price': away_price},
                             ]

        # CS market
        CSmarket = markets.xpath('div[@class="block-header-wrapper"]/div/'
                                 'span[@class="block-title" and text()="Correct Score"]/'
                                 '../../../div[@class="football-matches"]')
        CSresults = CSmarket.xpath('div[starts-with(@class, "match-row-grouped ")]/'
                                   'div[@class="match featured-match featured-match-row"]/'
                                   'div')
        CSdict = {'marketName': 'Correct Score', 'runners': []}
        for result in CSresults:
            runnerName = take_first(result.xpath('div[@class="bet-title-3row"]/text()').extract())
            price = take_first(result.xpath('div[@class="home-odds"]/div/'
                                            'span[@class="odds-fractional"]/text()').extract())
            if runnerName and price:
                CSdict['runners'].append({'runnerName': runnerName, 'price': price})

        # Add markets
        l.add_value('markets', [MOdict, CSdict])

        # Load item
        return l.load_item()
