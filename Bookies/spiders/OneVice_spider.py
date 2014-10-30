from __future__ import division
from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from scrapy.http import Request
from Bookies.help_func import am2dec
from Bookies.help_func import chunks
import re
take_first = TakeFirst()


class OneviceSpider(Spider):
    name = "Onevice"
    allowed_domains = ["1vice.ag"]

    # Visit the homepage first
    def start_requests(self):
        yield Request(url='http://www.1vice.ag',
                      callback=self.get_sports
                      )

    def get_sports(self, response):
        # request sports page
        yield Request(url='http://www.1vice.ag/?page_id=17',
                      callback=self.get_leagues
                      )

    def get_leagues(self, response):
        # request leagues page
        yield Request(url='http://backend.1vice.ag/livelines.aspx',
                      headers={'Referer': 'http://www.1vice.ag/?page_id=17'},
                      callback=self.parse_leagues
                      )

    def parse_leagues(self, response):

        footballMenu = response.xpath('//ul[@id="menuLiveLines"]/li[starts-with(text(),"SOCCER -")]')
        leagues = []
        for menu in footballMenu:
            links = menu.xpath('ul/li/a/@href').extract()
            lnames = menu.xpath('ul/li/a/text()').extract()  # useful for filter
            lpairs = zip(lnames, links)
            leagues.extend(lpairs)

        headers = {'Referer': 'http://backend.1vice.ag/livelines.aspx?wmode=transparent',
                   'Host': 'backend.1vice.ag'}
        base_url = 'http://backend.1vice.ag/'
        for league in leagues:
            GETstr = league[-1]
            yield Request(url=base_url+GETstr, headers=headers,
                          callback=self.parse_Data)

    def parse_Data(self, response):

        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        # Unlike most scrapes there is no detail page for each event, just a
        # listing of markets. We grab the MO, totals and goals type markets for
        # each event (each triplet), but this event may be repeated again with
        # further, different totals or goals markets, so at the end we have to
        # consolidate markets to single event. Also half time versions are dealt
        # with.
        rows = response.xpath('//tr[@class="TrGameOdd" or @class="TrGameEven"]')
        events = list(chunks(rows, 3))
        eventDics = []
        for evt in events:
            eventDic = {}

            team1 = take_first(evt[0].xpath('td[4]/text()').extract())
            team2 = take_first(evt[1].xpath('td[4]/text()').extract())
            teams = [team1, team2]
            eventDic['teams'] = teams

            dateTime = take_first(evt[0].xpath('td[2]/text()').extract())
            eventDic['dateTime'] = dateTime

            eventDic['markets'] = []
            # This regex matches names like o3.75, u.75, o2 and prices like +110
            # or EV.
            Tregex = re.compile("(?P<name>[ou](\d+)?(.\d+)?)(?P<price>([+-]\d+|EV))")
            # Similar to Tregex but also matches PK as name.
            Gregex = re.compile("(?P<name>([+-](\d+)?(.\d+)?|PK))(?P<price>([+-]\d+|EV))")
            for ind in ['5', '6', '7']:
                # index 5 in MO, 6 is totals, 7 is goals
                # NB for Totals and Goals (i.e. ind 6 or 7) the home_price and
                # away_price are really combinations of name and price.
                home_price = take_first(evt[0].xpath('td['+ind+']/text()').extract())
                away_price = take_first(evt[1].xpath('td['+ind+']/text()').extract())
                draw_price = take_first(evt[2].xpath('td['+ind+']/text()').extract())
                if ind == '5' and home_price and away_price and draw_price:
                    marketName = 'Match Odds'
                elif ind == '6' and home_price and away_price:
                    marketName = 'Totals'
                elif ind == '7' and home_price and away_price:
                    marketName = 'Goals'
                else:
                    continue

                # Make sure half time markets have this in marketName, then
                # remove it from team names themselves
                if '1ST HALF' in team1 or ' 1ST HALF' in team2:
                    marketName += ' 1ST HALF'
                    eventDic['teams'] = [n.replace(' 1ST HALF', '') for n in teams]

                if 'Match Odds' in marketName:
                    mdict = {'marketName': marketName, 'runners': []}
                    mdict['runners'] = [{'runnerName': 'HOME',
                                        'price': am2dec(home_price)},
                                        {'runnerName': 'DRAW',
                                        'price': am2dec(draw_price)},
                                        {'runnerName': 'AWAY',
                                        'price': am2dec(away_price)},
                                        ]

                    eventDic['markets'].append(mdict)
                else:
                    home_price = home_price.encode('utf8').replace('\xc2\xbd', '.5') \
                                                          .replace('\xc2\xbc', '.25') \
                                                          .replace('\xc2\xbe', '.75')
                    away_price = away_price.encode('utf8').replace('\xc2\xbd', '.5') \
                                                          .replace('\xc2\xbc', '.25') \
                                                          .replace('\xc2\xbe', '.75')
                    regex = None
                    if ind == '6':
                        # Totals
                        regex = Tregex
                    elif ind == '7':
                        # Goals
                        regex == Gregex
                    if regex:
                        home = regex.search(home_price)
                        away = regex.search(away_price)
                        if home and away:
                            home_name = home.groupdict()['name']
                            home_price = am2dec(home.groupdict()['price'])
                            away_name = away.groupdict()['name']
                            away_price = am2dec(away.groupdict()['price'])
                            marketName += ' '+home_name+'/'+away_name
                            mdict = {'marketName': marketName, 'runners': []}
                            mdict['runners'] = [{'runnerName': home_name,
                                                'price': home_price},
                                                {'runnerName': away_name,
                                                'price': away_price},
                                                ]
                            eventDic['markets'].append(mdict)
                        else:
                            log.msg('No regex match: home: %s, away:%s'
                                    % (home_name, away_name), level=log.ERROR)
                            log.msg('Teams: %s, %s' % (team1, team2), level=log.ERROR)

            eventDics.append(eventDic)

            # Finally consolidate all markets with same teams and date.
            newDics = []
            for eD1 in eventDics:
                new_eD = {'teams': eD1['teams'], 'dateTime': eD1['dateTime'],
                          'markets': []
                          }
                mkts = [e['markets'] for e in eventDics if e['teams'] == eD1['teams']
                        and e['dateTime'] == eD1['dateTime']]
                # flatten
                mkts = [item for sublist in mkts for item in sublist]
                new_eD['markets'] = mkts
                # if not appended already add it
                if ((new_eD['teams'], new_eD['dateTime']) not in
                   [(d['teams'], d['dateTime']) for d in newDics]):
                    newDics.append(new_eD)

        nevents = []
        for nevent in newDics:
            l = EventLoader(item=EventItem2(), response=response)
            l.add_value('sport', u'Football')
            l.add_value('bookie', self.name)
            l.add_value('dateTime', nevent['dateTime'])
            l.add_value('teams', nevent['teams'])
            l.add_value('markets', nevent['markets'])
            nevents.append(l.load_item())

        return nevents
