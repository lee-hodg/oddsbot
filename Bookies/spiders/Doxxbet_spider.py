from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
# from Bookies.help_func import linkFilter
from scrapy.http import Request
import re
take_first = TakeFirst()


class DoxxbetSpider(Spider):
    name = "Doxxbet"

    # URL with soccer comp click req
    start_urls = ['https://www.doxxbet.com/en/sports-betting/']

    # Another option here would have been use crawlspider with "process_value"
    # on each competition link found, to extract onclick params, construct
    # loadUrl then return the url. See link-extractors docs.
    def parse(self, response):

        # Notice this xpath selector uses the 'li[a/text()="Soccer"]'
        # to only pick out li that have an 'a' with text "Soccer".
        # No matter what the order of the li, we get the right one.
        # league_names = response.xpath('//ul[@class="l1 nav"]/li[a/text()="Soccer"]/'
        #                               'ul[@class="l2 nav"]/li/ul[@class="l3 nav"]/'
        #                               'li/a[@class="item"]/text()').extract()
        jMethods = response.xpath('//ul[@class="l1 nav"]/li[a/text()="Soccer"]/'
                                  'ul[@class="l2 nav"]/li/ul[@class="l3 nav"]/'
                                  'li/a[@class="item"]/@href').extract()

        cupIdsList = []
        for method in jMethods:
            matches = re.findall(r"loadLC\((\d+?)\)", method)
            if matches:
                cupIdsList.append(matches[0])

        # league_pairs = zip(league_names, cupIdsList)
        # For each cup Id build the ajax request
        # hopefully the cookie will be set when visted sports betting page.
        base_url = 'https://www.doxxbet.com/ajax/bets.aspx'
        headers = {'Referer': 'https://www.doxxbet.com/en/sports-betting/',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Host': 'www.doxxbet.com',
                   }

        for cid in cupIdsList:
            GETstr = '?ResetChanceTypeGroupSelection=1&LeagueCupID='+str(cid)+'&AnchorID=oddFilter'
            yield Request(url=base_url+GETstr, headers=headers, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):
        moreLinks = response.xpath('//table/tr/td[@class="nav"]/a[1][not(@class="stats")]/@href').extract()

        regex = re.compile("javascript:loadEvent\((?P<eid>\d+),'(?P<anchid>\w+)'\)")
        moreTupleList = []
        for link in moreLinks:
            r = regex.search(link)
            eid = r.groupdict()['eid']
            anchid = r.groupdict()['anchid']
            moreTupleList.append((eid, anchid))

        base_url = 'https://www.doxxbet.com/ajax/eventDetail.aspx'
        headers = {'Host': 'www.doxxbet.com',
                   'Referer': response.url,
                   'X-Requested-With': 'XMLHttpRequest',
                   }
        for t in moreTupleList:
            GETstr = '?EventID=%s&AnchorID=%s' % (t[0], t[1])
            yield Request(url=base_url+GETstr, headers=headers,
                          callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:], level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        day = take_first(response.xpath('//div[@class="section first"]/div[@class="date"]/'
                                        'div[@class="cal"]/span[@class="day"]/text()').extract())
        month = take_first(response.xpath('//div[@class="section first"]/'
                                          'div[@class="date"]/div[@class="cal"]/'
                                          'span[@class="month"]/text()').extract())
        if day and month:
            dateTime = day+' '+month
        else:
            # Other format, e.g. Saturday
            dateTime = take_first(response.xpath('//div[@class="section first"]/'
                                                 'div[@class="date"]/text()').extract())
        l.add_value('dateTime', dateTime)

        teams = response.xpath('//div[@id="eventDetailTitle"]/h3/span[@class="name"]/text()').extract()
        l.add_value('teams', teams)

        # Markets
        mkts = response.xpath('//table[starts-with(@class, "oddTbl")]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('tr[@class="name"]/th/text()').extract())
            mdict = {'marketName': marketName, 'runners': []}
            if 'Correct Score' in marketName or 'Halftime / Fulltime' in marketName:
                runners = mkt.xpath('tr[not(starts-with(@class, "result")) and not(@class="name")]/td/a')
                for runner in runners:
                    runnerName = take_first(runner.xpath('span[@class="name"]/text()').extract())
                    price = take_first(runner.xpath('span[@class="odd"]/text()').extract())
                    mdict['runners'].append({'runnerName': runnerName, 'price': price})
            else:
                runnerNames = mkt.xpath('tr[starts-with(@class, "result")]/th/text()').extract()
                if not runnerNames:
                    # Sometimes a span
                    runnerNames = mkt.xpath('tr[starts-with(@class, "result")]/th/span/text()').extract()
                prices = mkt.xpath('tr[not(starts-with(@class, "result")) and not(@class="name")]/'
                                   'td/a/text()').extract()
                runners = zip(runnerNames, prices)
                for runner in runners:
                    mdict['runners'].append({'runnerName': runner[0], 'price': runner[1]})
            allmktdicts.append(mdict)

        # Do some Doxxbet specific post processing and formating
        for mkt in allmktdicts:
            if 'Result' == mkt['marketName']:
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
        return l.load_item()
