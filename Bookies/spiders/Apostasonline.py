# -*- coding: utf-8 -*-
from __future__ import division
# import locale  # Porteugeuse dates
from scrapy.spider import Spider
from Bookies.loaders import EventLoader
from Bookies.items import EventItem2
from scrapy.contrib.loader.processor import TakeFirst
from scrapy import log
from Bookies.help_func import linkFilter
from scrapy.http import Request
take_first = TakeFirst()


def convMonth(date):
    '''
    Very bizarrely this bookie
    sometimes uses English months
    and Porteeuguse days, and sometimes
    not, sometimes all porteuguse.
    Dirty soln: convert any english month
    to port and then parse based on portegeuse.
    '''
    monthDict = {'January': 'Janeiro',
                 'February': 'Fevereiro',
                 'March': 'Março',
                 'April': 'Abril',
                 'May': 'Maio',
                 'June': 'Junho',
                 'July': 'Julho',
                 'August': 'Agosto',
                 'September': 'Setembro',
                 'October': 'Outubro',
                 'November': 'Novembro',
                 'December': 'Dezembro',
                 }
    for key in monthDict.keys():
        if key in date:
            return date.replace(key, monthDict[key])
    return date


class ApostasonlineSpider(Spider):

    name = "Apostasonline"

    # Visit the homepage first
    def start_requests(self):
        yield Request(url='https://www.apostasonline.com/',
                      callback=self.parseLeague)

    def parseLeague(self, response):

        lpairs = []
        league_lis = response.xpath('//li[@class="sport_240"]/ul/li/ul/li')
        for li in league_lis:
            leagueName = take_first(li.xpath('a/text()').extract())
            leagueId = take_first(li.xpath('a//@data-id').extract())
            lpairs.append((leagueName, leagueId))

        leagueIds = [lId for (lName, lId) in lpairs
                     if not linkFilter(self.name, lName)]
        # Build req
        base_url = 'https://www.apostasonline.com/pt-PT/sportsbook/eventpaths/multi/'
        headers = {'Referer': 'https://www.apostasonline.com/',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Host': 'www.apostasonline.com'}
        for lid in leagueIds:
            GETstr = '[%s]?ajax=true&timezone=undefined' % lid
            yield Request(url=base_url+GETstr, headers=headers,
                          callback=self.pre_parseData, dont_filter=True)

    def pre_parseData(self, response):
        moreLinks = response.xpath('//div[@data-hook="more_markets"]/a/@href').extract()
        base_url = 'https://www.apostasonline.com/'
        GETstr = '?ajax=true&timezone=undefined'
        headers = {'Referer': 'https://www.apostasonline.com/',
                   'X-Requested-With': 'XMLHttpRequest',
                   'Host': 'www.apostasonline.com'}
        for link in moreLinks:
            yield Request(url=base_url+link+GETstr, headers=headers,
                          callback=self.parseData, dont_filter=True)

    def parseData(self, response):
        log.msg('Going to parse data for URL: %s' % response.url[20:],
                level=log.INFO)

        l = EventLoader(item=EventItem2(), response=response)
        l.add_value('sport', u'Football')
        l.add_value('bookie', self.name)

        dateTime = take_first(response.xpath('//hgroup/h1/time/@datetime').extract())
        l.add_value('dateTime', dateTime)

        eventName = response.xpath('//hgroup/h1/text()').extract()
        eventName = ''.join([s.strip() for s in eventName])
        if eventName:
            teams = eventName.lower().split(' - ')
            l.add_value('teams', teams)

        # Markets
        mkts = response.xpath('//div[starts-with(@class, "rollup market_type market_type_id_")]')
        allmktdicts = []
        for mkt in mkts:
            marketName = take_first(mkt.xpath('div[@class="market_type_title"]/h2/'
                                              'text()').extract())
            mdict = {'marketName': marketName, 'runners': []}
            runners = mkt.xpath('.//tr[@class="event"]/td[starts-with(@class, "outcome outcome_")]')
            for runner in runners:
                runnername = take_first(runner.xpath('a/div/span[starts-with(@class, "name")]/text()').extract())
                price = take_first(runner.xpath('a/@data-price-decimal').extract())
                mdict['runners'].append({'runnerName': runnername, 'price': price})
            allmktdicts.append(mdict)

        # Do some Apostas specific post processing and formating
        for mkt in allmktdicts:
            if '1X2 - 90 Min' in mkt['marketName']:
                mkt['marketName'] = 'Match Odds'
                for runner in mkt['runners']:
                    if teams[0] in runner['runnerName'].lower():
                        runner['runnerName'] = 'HOME'
                    elif teams[1] in runner['runnerName'].lower():
                        runner['runnerName'] = 'AWAY'
                    elif 'empate' in runner['runnerName'].lower():
                        runner['runnerName'] = 'DRAW'
            elif u'Resultado exato' in mkt['marketName']:
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
