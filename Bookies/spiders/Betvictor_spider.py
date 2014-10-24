from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
# from Betvictor_script import process_script
from scrapy.spider import Spider
from Bookies.items import EventItem2
from Bookies.loaders import EventLoader
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request  # , FormRequest
take_first = TakeFirst()


#
# Betvictor uses a js challenge when accessing page
# for first time, if passed it sets the cookie and grants
# access. See myNotes/Betvictor_writeup.txt for more.
# But in brief, we rip the params from the initial
# challenge response, simulate the js, uses the script
# imported, then make a POST request, taking care
# to use a tuple so that order in the param string
# is kept!.
#
# There is also a loophole that adding '/' to end
# of URL seems to bypass the need for any of this
# ; even if simple GET requests are just used, if
# the trailing slash is used the server serves content.
# However, I keep the js challenge in place in case they
# plug this hole in future.
#
# They have updated to use a new js challenge breaking my process_script,
# the '/' loophole still works though, so for now I will use that
# If they stop that loophole in the future, hopefully I will be less
# busy and can spend a day or two doing a new challenge emulator.
#


class BetVictorSpider(Spider):
    name = "Betvictor"
    allowed_domains = ["betvictor.com"]

    # Visit the football homepage first to GET the
    # challenge response.
    def start_requests(self):
        yield Request(url='http://www.betvictor.com/sports/en/football/',
                      callback=self.parse_leagues
                      )

    # def challenge(self,response):

    #     # Rip params from js, simulate computation,
    #     # return the TS644333_75 POST param needed.
    #     value = process_script(response)
    #     log.msg('Challenge value TS01644333_cr: %s'  % value, level=log.INFO)

    #     # Order is important when POSTing to sim the
    #     # hidden form, hence use tuple of pairs, rather
    #     # than dict. MAKE SURE in paros that this order
    #     # matches firefox order via proxy.
    #     orderedData= (
    #                    ('TS01644333_id', '3'),
    #                    ('TS01644333_cr', str(value)),  #('TS644333_75', str(value)),
    #                    ('TS01644333_76', '0'),
    #                    ('TS01644333_md', '1'),
    #                    ('TS01644333_rf', '0'),
    #                    ('TS01644333_ct', '0'),
    #                    ('TS01644333_pd', '0'),
    #                  )
    #     yield FormRequest(url='http://www.betvictor.com/sports/en/football',
    #                       formdata=orderedData,
    #                       headers={'Content-Type': 'application/x-www-form-urlencoded'},
    #                       callback=self.parse_leagues
    #                       )

    def parse_leagues(self, response):

        # 4428 seem to be match odds
        # /sports/en/football/sco-championship/coupons/100/6265610/0/4428/0/PE/0/0/0/0/1
        sx = SgmlLinkExtractor(allow=[r'http://www.betvictor.com/sports/en/'
                                      'football/[A-Za-z0-9-]+/coupons/100/[0-9]+/0/4428/0/PE/0/0/0/0/1'
                                      ])
        league_links = sx.extract_links(response)

        # For premier league  and spanish premier a GET req here is fine, but again
        # the '/' is needed otherwise, chlg presented again, might aswell just
        # add it for all leagues
        for link in league_links:
            l = link.url+'/'
            yield Request(l, callback=self.pre_parse_Data)

    def pre_parse_Data(self, response):

        # More links
        moreLinks = response.xpath('//table/tbody/tr[@class="body"]/'
                                   'td[@class="more"]/a/@href').extract()
        base_url = 'http://www.betvictor.com'
        headers = {'Host': 'www.betvictor.com',
                   'Referer': response.url}
        for link in moreLinks:
            yield Request(url=base_url+link, headers=headers,
                          callback=self.parse_Data, dont_filter=True)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//div[@id="center_content"]/'
                                             'div[@class="coupon_header scrollable"]/'
                                             'div[@class="coupon_header_titles"]/'
                                             'h4/span/text()').extract())

        l.add_value('dateTime', dateTime)

        eventName = take_first(response.xpath('//div[@id="center_content"]/'
                                              'div[@class="coupon_header scrollable"]/'
                                              'div[@class="coupon_header_titles"]/'
                                              'h1/@title').extract())
        if eventName:
            teams = eventName.lower().split(' v ')
            l.add_value('teams', teams)

        # Markets
        mkts = response.xpath('//div[@class="single_markets" or @class="multiple_markets"]/'
                              'div[starts-with(@id, "coupon")]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('h4/text()').extract())
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt.xpath('table[not(@class="has_group_date")]/'
                                'tbody/tr[not(@class="header")]/td[@class="outcome_td"]')
            for runner in runners:
                runnerName = take_first(runner.xpath('span/@data-outcome_description').extract())
                price = take_first(runner.xpath('span/a/span[@class="price"]/text()').extract())
                mdict['runners'].append({'runnerName': runnerName, 'price': price})
            allmktdicts.append(mdict)

        # Do some Betvic specific post processing and formating
        for mkt in allmktdicts:
            if 'Match Betting'in mkt['marketName']:
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0] in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1] in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'Draw' in runner['runnerName']:
                        runner['runnerName'] = 'DRAW'
            elif 'Correct Score - 90 Mins' in mkt['marketName']:
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
