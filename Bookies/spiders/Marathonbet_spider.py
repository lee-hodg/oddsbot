from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
# from scrapy.http import Request
from scrapy.http import FormRequest
from scrapy.selector import Selector
import json
take_first = TakeFirst()


class MarathonbetSpider(Spider):
    '''
    Notes: if you use http instead of https get 301
    redirects.
    '''

    name = "Marathonbet"
    allowed_domains = ["marathonbet.com"]
    start_urls = ['https://www.marathonbet.com/en/betting/Football/']

    #  First get the league links
    def parse(self, response):

        log.msg('Grabbing all events..')
        eventSelection = response.xpath('//table[@class="foot-market"]//tbody/'
                                        'tr[@class="event-header"]')
        base_url = 'https://www.marathonbet.com/en/markets.htm'
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                   'Host': 'www.marathonbet.com',
                   'Referer': 'https://www.marathonbet.com/en/betting/Football/',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Cache-Control': 'no-cache',
                   'Connection': 'keep-alive',
                   'Pragma': 'no-cache',
                   'DNT': '1',
                   # 'X-NewRelic-ID': 'Vg8OWFJACwYCXFJXBg==',
                   }

        for event in eventSelection:
            # Get tree id make POST for more data
            treeId = take_first(event.xpath('td[starts-with(@class,"first")]/table/tr//'
                                            'td[@class="more-view"]/a/@treeid').extract())
            if treeId:
                yield FormRequest(url=base_url, formdata={'treeId': treeId},
                                  headers=headers, callback=self.parseEvent,
                                  meta={'treeId': treeId},
                                  dont_filter=True)
            else:
                continue

    def parseEvent(self, response):

        log.msg('Going to parse data for treeId: %s' % response.meta['treeId'],
                level=log.DEBUG)

        # Resp is HTML wrapped in JSON
        jResp = json.loads(response.body)
        htmlResp = jResp['HTML_ROW_WITH_ADDITIONAL_MARKETS']
        # Get selector from this unicode string
        sel = Selector(text=htmlResp)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(sel.xpath('//td[starts-with(@class,"first")]/'
                                        'table/tr//td[@class="date"]/text()').extract())
        l.add_value('dateTime', dateTime)

        team1 = take_first(sel.xpath('//td[@class="name" or @class="today-name"]'
                                     '/span/div[1]/text()').extract())
        team2 = take_first(sel.xpath('//td[@class="name" or @class="today-name"]'
                                     '/span/div[2]/text()').extract())
        if team1 and team2:
            l.add_value('teams', [team1, team2])

        # Markets
        markets = sel.xpath('//div[@class="block-market-table-wrapper"]'
                            '/div[@class="market-inline-block-table-wrapper"]')
        # MO market first
        # Get table associated with the td that has a p with text "Match"
        # (remember xpath .. means move up just like linux fs)
        MOdict = {'marketName': 'Match Odds'}
        # N.B. you may consider using [contains(text(), "Result")], but this
        # matches other markets.
        MOtable = markets.xpath('div[@class="market-table-name"]/'
                                'div[@class="name-field"][text()=" Result "]/../../table')
        home_price = take_first(MOtable.xpath('tr[1]/td[2]/span/text()').extract())
        draw_price = take_first(MOtable.xpath('tr[2]/td[2]/span/text()').extract())
        away_price = take_first(MOtable.xpath('tr[3]/td[2]/span/text()').extract())
        MOdict['runners'] = [{'runnerName': 'HOME',
                             'price': home_price},
                             {'runnerName': 'DRAW',
                              'price': draw_price},
                             {'runnerName': 'AWAY',
                              'price': away_price},
                             ]

        # CS market
        CSdict = {'marketName': 'Correct Score', 'runners': []}
        CStable = markets.xpath('div[@class="market-table-name"]/div[@class="name-field"]'
                                '[text()=" Correct Score "]/../../table')
        CShomeRes = CStable.xpath('tr/td[1]/div[contains(@class, "coeff-link-3way")]')
        CSdrawRes = CStable.xpath('tr/td[2]/div[contains(@class, "coeff-link-3way")]')
        CSawayRes = CStable.xpath('tr/td[3]/div[contains(@class, "coeff-link-3way")]')

        for result in CShomeRes:
            # Column where home team has winning score (strip brackets in loader)
            runnerName = take_first(result.xpath('div[@class="coeff-handicap"]/text()').extract())
            price = take_first(result.xpath('div[@class="coeff-price"]/span/text()').extract())
            CSdict['runners'].append({'runnerName': runnerName,
                                      'price': price, 'reverse_tag': False})

        for result in CSdrawRes:
            # Column for draw
            runnerName = take_first(result.xpath('div[@class="coeff-handicap"]/text()').extract())
            price = take_first(result.xpath('div[@class="coeff-price"]/span/text()').extract())
            CSdict['runners'].append({'runnerName': runnerName,
                                      'price': price, 'reverse_tag': False})

        for result in CSawayRes:
            # Column for away (needs reversing)
            runnerName = take_first(result.xpath('div[@class="coeff-handicap"]/text()').extract())
            price = take_first(result.xpath('div[@class="coeff-price"]/span/text()').extract())
            CSdict['runners'].append({'runnerName': runnerName,
                                      'price': price, 'reverse_tag': True})
        # Add markets
        l.add_value('markets', [MOdict, CSdict])

        # Load item
        return l.load_item()
