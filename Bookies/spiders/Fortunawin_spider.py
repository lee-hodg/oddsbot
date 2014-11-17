from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


class FortunawinSpider(Spider):

    name = "Fortunawin"
    allowed_domains = ["fortunawin.com"]

    # Visit the football homepage first
    def start_requests(self):
        yield Request(url='http://www.fortunawin.com/en/betting/',
                      callback=self.parse_leagues
                      )

    def parse_leagues(self, response):

        # Use some regex to deny certain links
        denyList = [(r'http://www\.fortunawin\.com/en/betting/football/'
                     '[a-z0-9A-Z-]*(qualification|Winner|standings|season)[a-z0-9A-Z-]*'), ]
        sx = SgmlLinkExtractor(allow=[r'http://www.fortunawin.com/en/betting/football/([1-9]?)[A-Za-z-]'],
                               deny=denyList)
        league_links = set([link.url for link in sx.extract_links(response)])

        headers = {'Host': 'www.fortunawin.com',
                   'Referer': response.url}
        for link in league_links:
            yield Request(link, headers=headers, callback=self.pre_parse_Data,
                          dont_filter=True)

    def pre_parse_Data(self, response):

        base_url = 'http://www.fortunawin.com'
        headers = {'Host': 'www.fortunawin.com',
                   'Referer': response.url,
                   'X-Requested-With': 'XMLHttpRequest'
                   }
        events = response.xpath('//tr[starts-with(@id, "bet-")]')
        for event in events:
            moreLink = take_first(event.xpath('td[@class="col_toggle"]/'
                                              'a[starts-with(@id, "toggler-id-")]/@href').extract())
            dateTime = take_first(event.xpath('.//span[starts-with(@id, "datetime-")]/text()').extract())
            dateTime = take_first(dateTime.strip().replace('.', '/').rsplit('/', 1))
            eventName = take_first(event.xpath('.//td[@class="col_title"]/'
                                               'div/span/a/text()').extract())
            # print eventName
            # if 'Antalyaspor' in eventName:
            #    print response.url
            #    stop = raw_input('e2c')
            MOdict = {'marketName': 'Match Odds', 'runners': []}
            home_price = take_first(event.xpath('td[2]/a/@data-rate').extract())
            draw_price = take_first(event.xpath('td[3]/a/@data-rate').extract())
            away_price = take_first(event.xpath('td[4]/a/@data-rate').extract())
            MOdict['runners'] = [{'runnerName': 'HOME',
                                  'price': home_price},
                                 {'runnerName': 'DRAW',
                                 'price': draw_price},
                                 {'runnerName': 'AWAY',
                                 'price': away_price},
                                 ]
            eventDic = {'eventName': eventName, 'dateTime': dateTime,
                        'MOdict': MOdict}
            if moreLink:
                yield Request(url=base_url+moreLink+'&ajax=1', headers=headers,
                            meta=eventDic, callback=self.parse_Data)
            else:
                # Write the MO market alone
                l = EventLoader(item=EventItem2(), response=response)
                l.add_value('sport', u'Football')
                l.add_value('bookie', self.name)
                if eventName:
                    teams = eventName.lower().split('-')
                    l.add_value('teams', teams)
                l.add_value('dateTime', dateTime)
                l.add_value('markets', [MOdict, ])
                # Load item
                yield l.load_item()


    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = response.meta['dateTime']
        l.add_value('dateTime', dateTime)

        eventName = response.meta['eventName']
        if eventName:
            teams = eventName.lower().split('-')
            l.add_value('teams', teams)

        # Markets
        MOdict = response.meta['MOdict']
        allmktdicts = [MOdict, ]
        tables = response.xpath('//table[starts-with(@id, "betTable--")]')
        blockTitle = ''
        block_col_heads = []
        for table in tables:
            title = take_first(table.xpath('thead/tr/th[@class="col_title_info"]/'
                                           'span/text()').extract())
            col_heads = table.xpath('thead/tr/th[@class="col_bet"]/span/text()').extract()
            if title:
                # Continue to use this title, and update title for block
                blockTitle = title
            else:
                # Use title for block
                title = blockTitle
            if col_heads:
                block_col_heads = col_heads
            else:
                col_heads = block_col_heads
            marketName = take_first(table.xpath('tbody/tr/td[@class="col_title"]/'
                                                'div/span/a/text()').extract())
            prices = table.xpath('tbody/tr/td[starts-with(@class, "col_bet")]/a/'
                                 '@data-rate').extract()
            mDict = {'marketName': title+' '+marketName, 'runners': []}
            headPrices = zip(col_heads, prices)
            for hP in headPrices:
                mDict['runners'].append({'runnerName': hP[0], 'price': hP[1]})
            allmktdicts.append(mDict)

        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
