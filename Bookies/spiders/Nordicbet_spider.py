from scrapy.spider import Spider
from scrapy.selector import Selector
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
import time
import json
import re
take_first = TakeFirst()


class NordicbetSpider(Spider):
    name = "Nordicbet"
    allowed_domains = ["nordicbet.com"]

    # Visit the football homepage set session cookie
    def start_requests(self):
        yield Request(url='https://www.nordicbet.com/eng/sportsbook',
                      callback=self.allfoot
                      )

    def allfoot(self, response):
        '''
        Request paginated page with all football links
        Could set NORDICBET_VIEW_MODE=all cookie to avoid needing paging?
        (Doesn't seem to really show all....)
        '''
        # ms since unix epoch stamp
        stamp = int(time.time()*1000)
        base_url = 'https://www.nordicbet.com/eng/sportsbook'
        GETstr = ('?cmd=chooseInAjax&category_id=50000000001&source=15&'
                  'sidebet_type=1x2&view_more_bets=true&_=%s' % stamp)
        headers = {'Host': 'www.nordicbet.com',
                   'Referer': 'https://www.nordicbet.com/eng/sportsbook',
                   'X-Requested-With': 'XMLHttpRequest'
                   }
        yield Request(url=base_url+GETstr, headers=headers, dont_filter=True,
                      callback=self.pageSport)

    def pageSport(self, response):
        '''
        Get the pagination data then
        iterate over all the pages requesting
        the football 1x2 events list for each
        '''

        # Now the next page if it exists
        try:
            # Pagination data
            jResp = json.loads(response.body)
            selPage = Selector(text=jResp['pagination'])
        except KeyError:
            # Only paging data with first hit
            pass

        # Get all paging info first hit and iterate over pages rather than recursive
        pages = selPage.xpath('//span[starts-with(@class, "page-number-common")]')
        for page in pages:
            # Other params needed
            stamp = int(time.time()*1000)
            nextPage = take_first(page.xpath('@rel').extract())
            bgameid = take_first(page.xpath('@begin_game_id').extract())
            egameid = take_first(page.xpath('@end_game_id').extract())
            bocsn = take_first(page.xpath('@begin_ocs_num').extract())
            eocsn = take_first(page.xpath('@end_ocs_num').extract())
            pcount = take_first(selPage.xpath('//span[@class="page_count_info"]/text()').extract())
            base_url = 'https://www.nordicbet.com/eng/sportsbook'
            GETstr = ('?cmd=chooseInAjax&category_id=50000000001&source=15&'
                      'target_page=%s&begin_game_id=%s&begin_ocs_num=%s&end_game_id=%s&'
                      'end_ocs_num=%s&page_count=%s&change_target=true&sidebet_type=1x2&'
                      'view_more_bets=true&_=%s' % (nextPage, bgameid, bocsn,
                                                    egameid, eocsn, pcount, stamp))
            headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                       'Host': 'www.nordicbet.com',
                       'Referer': 'https://www.nordicbet.com/eng/sportsbook',
                       'X-Requested-With': 'XMLHttpRequest',
                       }
            log.msg('The nextPage is: %s of %s' % (nextPage, int(pcount)))
            # log.msg('GETstr for page %s is %s' % (GETstr, int(nextPage)))
            # stop = raw_input('e2c')
            yield Request(url=base_url+GETstr, headers=headers, dont_filter=True,
                          meta={'page': nextPage},
                          callback=self.parse_events)

    def parse_events(self, response):
        '''
        Loop over all events. If no moreLink
        just yield the match odds data, if moreLink
        pass the MO data in meta and then request other markets
        data, finally adding all mkts in parseData
        '''

        pageNum = response.meta['page']
        log.msg('Parsing events for page: %s' % pageNum)

        try:
            jResp = json.loads(response.body)
            sel = Selector(text=jResp['selections'])
        except ValueError as e:
            log.msg('Error could not load JSON when paging? %s' % e,
                    level=log.ERROR)

        base_url = 'https://www.nordicbet.com/eng/sportsbook'
        headers = {'Host': 'www.nordicbet.com',
                   'Referer': 'https://www.nordicbet.com/eng/sportsbook',
                   'X-Requested-With': 'XMLHttpRequest'
                   }
        events = sel.xpath('//table[starts-with(@class, "resultstbl 1x2")]')
        for event in events:
            # Does event have moreLink?
            moreLink = take_first(event.xpath('tr/td/div[@class="extra"]/a').extract())
            # eventId needed for call for other markets (only if moreLink)
            eventClass = take_first(event.xpath('@class').extract())
            eId = eventClass.rsplit('_')[-1]

            # Build MO market and other event details
            # Get MO prices only and add to items ready to passed in meta
            # for insertion in parseData (first iteration of loop only)
            teams = []
            eventName = event.xpath('.//tr/td/div[@class="label"]/text()'
                                    '| .//tr/td/div[@class="label"]/a/text()').extract()
            eventName = ''.join([eN.strip() for eN in eventName])
            if eventName:
                teams = eventName.lower().split(' - ')

            dateTime = take_first(event.xpath('.//tr/td//span[@class="day"]/text()').extract())
            if not dateTime:
                # Could be live
                livelogo = event.xpath('.//tr/td[2]/div[@class="endingtime"]/div[@class="livebet_now_logo"]')
                if livelogo:
                    dateTime = 'Today'
                else:
                    log.msg('Error no dateTime could be grabbed')

            home_price = take_first(event.xpath('.//tr/td[4]//div[@class="odds_middle"]/text()').extract())
            draw_price = take_first(event.xpath('.//tr/td[5]//div[@class="odds_middle"]/text()').extract())
            away_price = take_first(event.xpath('.//tr/td[6]//div[@class="odds_middle"]/text()').extract())
            mDict = {'marketName': 'Match Odds',
                     'runners': [{'runnerName': 'HOME',
                                 'price': home_price},
                                 {'runnerName': 'DRAW',
                                 'price': draw_price},
                                 {'runnerName': 'AWAY',
                                 'price': away_price}
                                 ]
                     }
            if moreLink:
                # Pass along MOmarket and other event details, and make
                # request for more markets
                stamp = int(time.time()*1000)
                meta = {'teams': teams, 'eventName': eventName,
                        'dateTime': dateTime, 'mDict': mDict}
                # Make request for event detail
                GETstr = ('?cmd=chooseInAjax&sidebet_type=1x2&show_extra=true&'
                          'game_id=%s&source=15&_=%s' % (eId, stamp))

                yield Request(url=base_url+GETstr, headers=headers, meta=meta,
                              dont_filter=True, callback=self.parseData)
            else:
                # Just load the MO market only event
                l = EventLoader(item=EventItem2(), response=response)
                l.add_value('sport', u'Football')
                l.add_value('bookie', self.name)
                l.add_value('dateTime', dateTime)
                l.add_value('teams', teams)
                l.add_value('markets', [mDict, ])
                # Debug
                log.msg('No moreLink for %s, load MO prices only' % eventName, level=log.DEBUG)
                # log.msg('Datetime: %s' % dateTime, level=log.DEBUG)
                # log.msg('Teams %s' % teams, level=log.DEBUG)
                # log.msg('mDict: %s' % mDict, level=log.DEBUG)
                # Return loaded item
                # stop = raw_input('e2c')
                yield l.load_item()

    def parseData(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = response.meta['dateTime']
        l.add_value('dateTime', dateTime)

        teams = response.meta['teams']
        l.add_value('teams', teams)

        # Markets
        # There is not enough regularity for one-size-fits-all but could we
        # at least grab markets in groups sharing similar formatting (CS and
        # HT/FT for example)
        mktBlocks = response.xpath('//table[starts-with(@class, "resultstbl")]')
        allmktdicts = [response.meta['mDict'], ]  # Add in MO from meta
        underover_re = re.compile("Under/over: (?P<val>\d+\.\d+)")
        for mktBlock in mktBlocks:
            blockName = take_first(mktBlock.xpath('tr[1]/td[1]/div/text()').extract())

            if 'Under/over' in blockName:
                # Things are tricky because 'Under/over' or 'Under/over team'
                # is the grouping, but the marketName should actually be the row
                # label, i.e. 'Under/over 0.5', with runners 'Under 0.5', 'Over
                # 0.5'
                rows = mktBlock.xpath('tr[re:test(@class, "item$")]')
                for row in rows:
                    marketName = take_first(row.xpath('td[@class="label"]/div/text()').extract())
                    # If Under/over teams
                    if 'team' in blockName:
                        team = take_first(row.xpath('td[@align="left"]/text()').extract())
                        marketName = team+marketName
                    mDict = {'marketName': marketName, 'runners': []}
                    # Get the numeric over/under value
                    r = underover_re.search(marketName)
                    underover_val = r.groupdict()['val']
                    # Prices
                    uprice = take_first(row.xpath('td[@class="bet"]//div[@class="odds_middle"]/text()').extract())
                    oprice = take_first(row.xpath('td[@class="bet last"]//div[@class="odds_middle"]/text()').extract())
                    mDict['runners'].extend([{'runnerName': 'Under %s' % underover_val,
                                              'price': str(uprice),
                                              },
                                             {'runnerName': 'Over %s' % underover_val,
                                              'price': str(oprice)
                                              }
                                             ])
                    allmktdicts.append(mDict)

                if 'Exact score' == blockName or 'Halftime/fulltime' == blockName:
                    # N.B. Even half-time exact score different format!
                    if 'Exact score' == blockName:
                        marketName = 'Correct Score'
                    elif 'Halftime/fulltime' == blockName:
                        marketName = 'Halftime/Fulltime'
                    mDict = {'marketName': marketName, 'runners': []}
                    runners = mktBlock.xpath('tr[re:test(@class, "item$")]/'
                                             'td[@class="exact_result"]/'
                                             'table/tr/td[@align="center"]/'
                                             'table')
                    for runner in runners:
                        runnerName = take_first(runner.xpath('td[1]/text()').extract())
                        price = take_first(runner.xpath('td[2]//div[@class="odds_middle"]/'
                                                        'text()').extract())
                        mDict['runners'].append({'runnerName': runnerName,
                                                 'price': price})

                    allmktdicts.append(mDict)

        # # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        return l.load_item()
