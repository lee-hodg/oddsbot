from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


class BetwaySpider(Spider):

    name = "Betway"
    allowed_domains = ["betway.com"]
    start_urls = ['https://sports.betway.com/#/soccer/international/friendlies']

    # First get the league links
    def parse(self, response):

        # Use some ninja xpath to get only li for soccer
        li = response.xpath('//div[@id="oddsmenu-inner"]/ul[@class="parent"]/'
                            'li[descendant::div[@class="section "]/a[@id="betclass_soccer"]]')
        # league links:
        league_links = li.xpath('ul[@class="child"]/li/ul/li//a/@href').extract()

        # Remove unwanted links, returns True to filter out link.
        league_links = [link for link in league_links if not linkFilter(self.name, link)]

        base_url = 'https://sports.betway.com/?u='
        headers = {'Referer': 'https://sports.betway.com/',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Host': 'sports.betway.com',
                   }
        for link in league_links:
            yield Request(url=base_url+link+'&m=win-draw-win', headers=headers,
                          callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)
        # Betway has very annoying display for each league,
        # with all events of certain date under that date block head.
        tableRows = response.xpath('//tbody[@class="oddsbody"]/tr')

        # For all rows under with no date will use latest blockdate,
        # single item list to match xpath extract
        blockdate = []
        items = []
        for row in tableRows:
            # Test with xpath if date row by seeing if td has parent
            # tr with class date. Surely  easier way to just check self?
            if take_first(row.xpath('@class').extract()) and 'date' in take_first(row.xpath('@class').extract()):
                blockdate = row.xpath('td/text()').extract()
            else:
                # Else test if this is an 'event' row, using time as
                # criteria.
                rowtime = row.xpath('td[@class="market_title"]/div[1]/text()').extract()  # 24hr
                if rowtime != []:

                    # We have event.
                    l = EventLoader(item=EventItem2(), response=response)
                    l.add_value('sport', u'Football')
                    l.add_value('bookie', self.name)

                    dateTime = take_first(blockdate)
                    l.add_value('dateTime', dateTime)

                    eventName = take_first(row.xpath('td[@class="market_title"]/'
                                                     'a/text()').extract())
                    if eventName:
                        teams = eventName.lower().split(' - ')
                        l.add_value('teams', teams)

                    # MO prices
                    MOdict = {'marketName': 'Match Odds'}
                    home_price = take_first(row.xpath('td[contains(@class,"outcome")][1]/'
                                                      'a[@class="outcome"]/'
                                                      'div[@class="outcome_button"]/text()').extract())

                    draw_price = take_first(row.xpath('td[contains(@class,"outcome")][2]/'
                                                      'a[@class="outcome"]/'
                                                      'div[@class="outcome_button"]/text()').extract())

                    away_price = take_first(row.xpath('td[contains(@class,"outcome")][3]/'
                                                      'a[@class="outcome"]/'
                                                      'div[@class="outcome_button"]/text()').extract())
                    MOdict['runners'] = [{'runnerName': 'HOME',
                                         'price': home_price},
                                         {'runnerName': 'DRAW',
                                         'price': draw_price},
                                         {'runnerName': 'AWAY',
                                         'price': away_price},
                                         ]
                    # Add markets
                    l.add_value('markets', [MOdict, ])

                    # Load item
                    items.append(l.load_item())

        return items
