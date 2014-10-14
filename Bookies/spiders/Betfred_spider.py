from scrapy.spider import Spider
from scrapy.selector import Selector
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from Bookies.loaders import EventLoader
from scrapy.http import Request
from scrapy import log
from Bookies.help_func import linkFilter
import time
take_first = TakeFirst()


# Betfred sim to Stanjames
# Need UK VPN
class BetfredSpider(Spider):
    name = "Betfred"
    allowed_domains = ["betfred.com"]

    # Visit the football homepage first to set session cookies
    def start_requests(self):
        yield Request(url='http://www.betfred.com/sport',
                      callback=self.pre_parse
                      )

    def pre_parse(self, response):
        # Make request to GET XML with all country market ids

        # UTC timestamp in milliseconds since unix epoch, not seconds.
        stamp = str(int(time.time() * 1000))

        base_url = 'http://www.betfred.com'
        GETstr = ('/__Admin/Proxy.aspx?proxyurl=http://warp.betfred.com/cache/'
                  'boNavigationList/2/UK/11.1.xml&_='+str(stamp))
        headers = {'Referer': 'http://www.betfred.com/sport',
                   'X-Requested-With': 'XMLHttpRequest'}

        yield Request(url=base_url+GETstr, headers=headers,
                      callback=self.traverseNav)

    def traverseNav(self, response):
        '''
        This will call itself back until
        we hit bottom rung of bonavigation tree
        '''
        log.msg('traverseNav is at %s' % response.url, level=log.INFO)
        bonav_nodes = response.xpath('//bonavigationnodes/bonavigationnode')
        markets = response.xpath('//marketgroups//marketgroup')
        if bonav_nodes and not markets:
            base_url = 'http://www.betfred.com'
            headers = {'Accept': 'application/xml, text/xml, */*; q=0.01',
                       'X-Requested-With': 'XMLHttpRequest',
                       'Referer': 'http://www.betfred.com/sport'}
            log.msg('traverseNav there ARE bonav nodes', level=log.INFO)
            # whilst still nodes, get id
            for n in bonav_nodes:
                bid = take_first(n.xpath('idfwbonavigation/text()').extract())
                bname = take_first(n.xpath('name/text()').extract())
                if linkFilter(self.name, bname):
                    # cont = raw_input('Ent to cont...')
                    continue
                # req next level
                stamp = str(int(time.time() * 1000))
                GETstr = ('/__Admin/Proxy.aspx?proxyurl=http://warp.betfred.com/cache/'
                          'boNavigationList/2/UK/'+str(bid)+'.xml&'+'_='+str(stamp))
                yield Request(url=base_url+GETstr, headers=headers,
                              callback=self.traverseNav)
        else:
            log.msg('traverseNav there are NO MORE bonav nodes', level=log.INFO)
            base_url = 'http://warp.betfred.com'
            headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                       'Referer': 'http://warp.betfred.com/UK/2/bettingsc?bettingscIndex=3'}
            # Hit bottom parse markets
            for market in markets:
                mname = take_first(market.xpath('name/text()').extract())
                if linkFilter(self.name, mname):
                    # cont = raw_input('Ent to cont...')
                    continue
                mid = take_first(market.xpath('idfwmarketgroup/text()').extract())
                log.msg('traverseNav making market req for market %s with id %s' % (mname, mid),
                        level=log.INFO)
                # For each marketId (i.e. each league) build AJAX GET request, to
                # receive back event data for that league in XML format. (lightMarketGroup
                # has no price data)
                GETstr = '/cache/marketGroup/UK/'+str(mid)+'.xml'
                yield Request(url=base_url+GETstr, headers=headers, callback=self.parse_Data)

    def parse_Data(self, response):

        sel = Selector(response)
        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)
        eventSelection = sel.xpath('//markets//market')
        log.msg('Number of events in Selection:  %s .' % len(eventSelection),
                level=log.INFO)

        items = []
        for event in eventSelection:
            l = EventLoader(item=EventItem2(), response=response)
            l.add_value('sport', u'Football')
            l.add_value('market', u'Match Odds')
            l.add_value('bookie', self.name)

            # '2014-03-24T18:00:00'
            dt = event.xpath('tsstart/text()').extract()
            l.add_value('dateTime', dt)

            eventName = take_first(event.xpath('eventname/text()').extract())
            if eventName:
                teams = eventName.lower().split(' v ')
                l.add_value('teams', teams)

            # Odds dict
            odd_dict = {}
            oddsSelection = event.xpath('selections//selection')
            for selection in oddsSelection:
                selType = take_first(selection.xpath('hadvalue/text()').extract())
                odd_up = take_first(selection.xpath('currentpriceup/text()').extract())
                odd_down = take_first(selection.xpath('currentpricedown/text()').extract())
                if odd_up and odd_down:
                    if selType == u'H':
                        odd_dict['odd1'] = odd_up+'/'+odd_down
                    elif selType == u'D':
                        odd_dict['odd3'] = odd_up+'/'+odd_down
                    elif selType == u'A':
                        odd_dict['odd2'] = odd_up+'/'+odd_down
            l.add_value('odds', odd_dict)

            items.append(l.load_item())
        return items
