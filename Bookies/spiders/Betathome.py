from scrapy.spider import Spider
from scrapy.selector import Selector
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
# from Bookies.help_func import linkFilter
import re
import json
take_first = TakeFirst()


def createMOonly(event, response, bookieName):
    '''
    Take event selection, parse dateTime, teams
    , MO prices then return event loaded.
    (Remember to load item one of the parse methods of spider class
    must return it, but this would terminate current chain, so we pass
    it along in a list, this function just create the item for appending
    to that list)
    '''

    teams = []
    eventName = take_first(event.xpath('td[1]/text()').extract())
    if eventName:
        teams = eventName.lower().split(' - ')
    dateTime = take_first(event.xpath('td[2]/text()').extract())
    home_price = take_first(event.xpath('td[3]/a/text()').extract())
    draw_price = take_first(event.xpath('td[4]/a/text()').extract())
    away_price = take_first(event.xpath('td[5]/a/text()').extract())
    mDict = {'marketName': 'Match Odds',
             'runners': [{'runnerName': 'HOME',
                         'price': home_price},
                         {'runnerName': 'DRAW',
                         'price': draw_price},
                         {'runnerName': 'AWAY',
                         'price': away_price}
                         ]
             }
    # Load the MO data
    l = EventLoader(item=EventItem2(), response=response)
    l.add_value('sport', u'Football')
    l.add_value('bookie', bookieName)
    l.add_value('dateTime', dateTime)
    l.add_value('teams', teams)
    l.add_value('markets', [mDict, ])
    # Debug
    log.msg('No more link for %s, load MO prices only' % eventName, level=log.DEBUG)
    log.msg('Datetime: %s' % dateTime, level=log.DEBUG)
    log.msg('Teams %s' % teams, level=log.DEBUG)
    log.msg('mDict: %s' % mDict, level=log.DEBUG)
    # Return loaded item
    return l.load_item()


class BetathomeSpider(Spider):
    name = "Betathome"

    # Visit the football homepage first
    def start_requests(self):
        yield Request(url='https://www.bet-at-home.com/en/sport',
                      callback=self.addSport)

    def addSport(self, response):
        '''
        Initial request to load (page 1 of) all football tips (MO markets)
        '''
        base_url = 'https://www.bet-at-home.com/svc/sport/AddSport'
        headers = {'Content-Type': 'application/json; charset=utf-8',
                   'Host': 'www.bet-at-home.com',
                   'Referer': 'https://www.bet-at-home.com/en/sport',
                   'X-Requested-With': 'XMLHttpRequest'
                   }
        yield Request(url=base_url, headers=headers, method='POST',
                      body=json.dumps({'sportId': '1'}),
                      callback=self.pageSport)

    def pageSport(self, response):
        '''
        Grab more links from page, add to dictionary passed with meta
        then jump to next page recursively calling back here to grab more moreLinks
        until no more next page, then finally iterate over the accumulated links
        sending each to parseData. Some events have no more link for these just
        grab MO data and pass item along in the meta to return at end.
        '''

        # First the moreLinks from this page
        # Resp is JSON, albeit just one key!
        jsonResp = json.loads(response.body)
        sel = Selector(text=jsonResp['d'])  # Since str obj not Response
        try:
            moreLinks = response.meta['moreLinks']
        except KeyError:
            moreLinks = []

        # Also need to deal with fact that if event has no moreLink
        # we still want the MO
        try:
            MOlist = response.meta['MOlist']
        except KeyError:
            MOlist = []
        events = sel.xpath('//table/tbody/tr')
        for event in events:
            moreLink = event.xpath('td[starts-with(@class, "ods-tbody-td ods-odd-additional")]/'
                                   'a/@href').extract()
            if moreLink:
                moreLinks += moreLink
            else:
                # parse MO only data here
                MOlist.append(createMOonly(event, response, self.name))

        # allMoreLinks += sel.xpath('//table/tbody/tr/'
        #                       'td[starts-with(@class, "ods-tbody-td ods-odd-additional")]/'
        #                       'a/@href').extract()
        # eventNames = sel.xpath('//table/tbody/tr/'
        #                        'td[1]/text()').extract()
        # log.msg('The eventNames are: \n %s' % (', '.join(eventNames)))

        # Now the next page if it exists
        # Two pagination panels, just take first...
        selPanel = take_first(sel.xpath('//div[@id="sportbetPageSelectorPanel"]'))
        # Now find nextPage numb if exists
        nextPage = take_first(selPanel.xpath('ul/li[@class="lil-item"]/'
                                             'a[re:test(@id, "AnchorNext$")]/'
                                             '@onclick').extract())
        if nextPage:
            b1 = nextPage.find('(')
            b2 = nextPage.find(')')
            nextPage = nextPage[b1+1: b2]
            nextPage = nextPage.rsplit(',')[-1]
            base_url = 'https://www.bet-at-home.com/svc/sport/DisplayPage'
            headers = {'Content-Type': 'application/json; charset=utf-8',
                       'Host': 'www.bet-at-home.com',
                       'Referer': 'https://www.bet-at-home.com/en/sport',
                       'X-Requested-With': 'XMLHttpRequest',
                       'Pragma': 'no-cache',
                       'Cache-Control': 'no-cache',
                       }
            log.msg('The nextPage is: %s and we have %i links' % (nextPage, len(moreLinks)))
            # stop = raw_input('e2c')
            # Recursive call
            yield Request(url=base_url, headers=headers, dont_filter=True,
                          meta={'page': nextPage, 'moreLinks': moreLinks, 'MOlist': MOlist},
                          method='POST',
                          body=json.dumps({'page': int(nextPage)}),
                          callback=self.pageSport)
        else:
            log.msg('We are on final page and we have %i links' % len(moreLinks))
            # No next page, so jump to parsing
            base_url = 'https://www.bet-at-home.com'
            headers = {'Host': 'www.bet-at-home.com',
                       'Referer': 'https://www.bet-at-home.com/en/sport',
                       }
            log.msg('Len of MOlist is %i' % len(MOlist))
            for n, link in enumerate(moreLinks):
                # Send the MOlist only on first
                if n == 0:
                    meta = {'MOlist': MOlist}
                    yield Request(url=base_url+link, headers=headers, dont_filter=True,
                                  meta=meta, callback=self.parseData)
                else:
                    yield Request(url=base_url+link, headers=headers, dont_filter=True,
                                  callback=self.parseData)

    def parseData(self, response):
        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//span[@class="h-fontWeightNormal h-fontSize-11-lineheight-13"]/'
                                             'text()').extract())
        dateTime = take_first(dateTime.split(','))
        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//span[@class="s-selected h-fontSize-14-lineheight-18"]/'
                                              'text()').extract())
        if eventName:
            teams = eventName.lower().split(' - ')
            l.add_value('teams', teams)

        # Markets
        mkts = response.xpath('//div[@class="rB S22G h-bG-FFFFFF l-mb3 l-overflowHidden"]')
        allmktdicts = []
        regex = re.compile("betslip3.OnTipClick\((?P<jData>.+)\)")
        for mkt in mkts:
            marketName = take_first(mkt.xpath('table/thead/tr/'
                                              'td[starts-with(@class, "ods-header")]//text()').extract())
            if not marketName:
                log.msg('No marketName, extract from: \n %s' % mkt.xpath('table/thead').extract())
                stop = raw_input('e2c')
            if 'Under/Over' in marketName or 'Handicap' in marketName:
                # Get handicap type
                htype = take_first(mkt.xpath('table/tbody/tr/td[1]/text()').extract())
                # Extract contents of (..)
                b1 = htype.find('(')
                b2 = htype.find(')')
                marketName += ' ' + htype[b1+1: b2]
            mDict = {'marketName': marketName, 'runners': []}
            runners = mkt.xpath('table/tbody/tr/td[starts-with(@class'
                                ', "ods-tbody-td")]/a/@onclick').extract()
            for runner in runners:
                r = regex.search(runner)
                dataDic = r.groupdict()['jData']
                dataJSON = json.loads(dataDic)
                runnerName = dataJSON['TipName']
                price = dataJSON['Odd']
                mDict['runners'].append({'runnerName': runnerName,
                                         'price': str(price),
                                         })
            allmktdicts.append(mDict)

        # Some Betathome specific formatting
        for mkt in allmktdicts:
            if mkt['marketName'] == 'Tip':
                mkt['marketName'] = 'Match Odds'
            for runner in mkt['runners']:
                if runner['runnerName'] == u'1':
                    runner['runnerName'] = 'HOME'
                elif runner['runnerName'] == u'2':
                    runner['runnerName'] = 'AWAY'
                elif runner['runnerName'] == u'X':
                    runner['runnerName'] = 'DRAW'

        # Add markets
        l.add_value('markets', allmktdicts)

        # Load item
        # If MOlist (MO only event items) in list load it too
        # This list should only be present once!
        try:
            MOlist = response.meta['MOlist']
            log.msg('MOlist recieved appended item to it')
            MOlist.append(l.load_item())  # in-place change
            return MOlist
        except KeyError:
            pass
        # Return just the detailed item
        return l.load_item()
