from __future__ import division  # so 5/2 gives 2.5 like in 3.X
from scrapy.contrib.loader import ItemLoader
from scrapy.contrib.loader.processor import TakeFirst, Compose, MapCompose, Identity
import dateutil.parser
import datetime
import re


# NB both input and output processors recieve iterator as first arg
# output can be anything. Result appended to internal list for that field
# alt Subclass the itemloader for different date formatting classes you
# encounter
def parse_str2date(dt_str):
    # parse datetime obj
    # could use loader context to specify locale
    # for foreign datestr see
    # http://doc.scrapy.org/en/latest/topics/loaders.html#item-loader-contexa
    # This can even parse stuff like 'Sat 3:00PM'
    # dts = []
    # for dt_str in dt_strs:
    #     if dt_str is not None and dt_str != '':
            # dts.append(dateutil.parser.parse(dt_str))
    # return dtsa
    # NB upper not lower so that GMT, BST work still
    dt_str = dt_str.upper()
    try:
        if 'TODAY' in dt_str:
            return datetime.datetime.now()
        elif 'TOMORROW' in dt_str:
            return datetime.datetime.now() + datetime.timedelta(days=1)

        return dateutil.parser.parse(dt_str)
    except:
        print '[ERROR parse_str2date] dt_str: %s .' % dt_str
        return dateutil.parser.parse('')


def parse_date2str(dt):
    # return str in whatever format
    # dt_strs = []
    FORMAT = '%m %d'
    # for dt in dts:
    #    if dt is not None:
    #        dt_strs.append(dt.strftime(FORMAT))
    # return dt_strs
    return dt.strftime(FORMAT)


class Strip(object):
    def __call__(self, values):
        for value in values:
            if value is not None and value != '':
                try:
                    return value.strip()
                except:
                    return value


# class StripOdds(object):
#     '''
#     odds field is dict we want to strip values only
#     '''
#     def __call__(self, dic):
#         return {k: v.lower().strip() for k, v in dic.iteritems()}


class StripMarketName(object):
    '''
    Strip marketName. In place change on dict passed
    '''
    def __call__(self, marketDic):
        try:
            marketDic['marketName'] = marketDic['marketName'].strip()
        except KeyError as e:
            print '\033[31m\033[7m [ERROR StripMarketName:] %s \033[0m' % e
        return marketDic


class StripOdds(object):
    '''
    Strip prices. In place change on dict passed
    '''
    def __call__(self, marketDic):
        try:
            for runner in marketDic['runners']:
                if runner['price']:
                    runner['price'] = runner['price'].strip()
        except KeyError as e:
            print '\033[31m\033[7m [ERROR StripOdds:] %s \033[0m' % e

        return marketDic

# class ConvertOdds(object):
#     '''
#     Covert odds to dec if not already dec
#     '''
#     evens_aliases = ['evs', 'evens', 'evns', 'ev', 'evn', 'even']
#
#     def __call__(self, odic):
#         for k, v in odic.iteritems():
#             # odds dic, replace commas by periods
#             v.replace(',', '.')
#
#             if v is None or v == '':
#                 odic[k] = '0.0'
#             elif v in self.evens_aliases:
#                 odic[k] = '2.0'
#             else:
#                 oList = [float(n) for n in v.split('/') if n is not '']
#                 if len(oList) is 0:
#                     # empty str
#                     odic[k] = '0.0'
#                 elif len(oList) is 1:
#                     try:
#                         odic[k] = '%.2f' % oList[0]
#                     except (ValueError, TypeError) as e:
#                         print '\033[31m\033[7m [ERROR ConvertOdds:] %s \033[0m' % e
#                 elif len(oList) is 2:
#                     odic[k] = '%.2f' % (1.00 + reduce((lambda x, y: x/y), oList))
#                 else:
#                     print ('\033[31m\033[7m [ERROR ConvertOdds:] too many /s:'
#                            'malformed price when convertOdds called \033[0m')
#         return odic


class FormatRunners(object):
    '''
    Convert CS runner names from
    "Liverpool 1-0" to just "1-0",
    trying to avoid regex for speed
    '''
    def __call__(self, marketDic):
        if marketDic['marketName'].title() != 'Correct Score':
            return marketDic
        else:
            for runner in marketDic['runners']:
                # Deal with numerous formats 'Liverpool 1-0', '1-0', '1:0',
                # 'Liverpool 1 - 0', 'Liverpool 1 : 0', 'liverpool 1:0', '(1-0)'
                # ( 1 - 0), 'Liverpool (1-0)', 'Liverpool (1 - 0)', 'Liverpool
                # (1 : 0)'.
                # Replace ':' with '-'
                # (slower than other methods perhaps, but deals with lots of
                # formats)
                regex = re.compile(r"(?P<score1>[0-9]+)\s*[\-,:]\s*(?P<score2>[0-9]+)")
                r = regex.search(runner['runnerName'])
                if r:
                    scoreDict = r.groupdict()
                    if 'reverse_tag' in runner.keys():
                        if runner['reverse_tag']:
                            # Reverse
                            runner['runnerName'] = '-'.join(scoreDict.values()[::-1])
                        else:
                            runner['runnerName'] = '-'.join(scoreDict.values())
                    else:
                        runner['runnerName'] = '-'.join(scoreDict.values())
            return marketDic


class ConvertOdds(object):
    '''
    Covert odds to dec if not already dec
    '''
    evens_aliases = ['evs', 'evens', 'evns', 'ev', 'evn', 'even']

    def __call__(self, marketDic):
        for runner in marketDic['runners']:
            v = runner['price']
            final = '0.0'

            # replace commas by periods
            if v:
                v = v.replace(',', '.')
                try:
                    v = v.lower()
                except AttributeError:
                    pass
                print v

            if v is None or v == '' or v == 'none':
                # 'none' occurs if v = None then str(v.lower())
                final = '0.0'
            elif v in self.evens_aliases:
                final = '2.0'
            else:
                oList = [float(n) for n in v.split('/') if n is not '']
                if len(oList) is 0:
                    # empty str
                    final = '0.0'
                elif len(oList) is 1:
                    try:
                        final = '%.2f' % oList[0]
                    except (ValueError, TypeError) as e:
                        print '\033[31m\033[7m [ERROR ConvertOdds:] %s \033[0m' % e
                elif len(oList) is 2:
                    final = '%.2f' % (1.00 + reduce((lambda x, y: x/y), oList))
                else:
                    print ('\033[31m\033[7m [ERROR ConvertOdds:] too many /s:'
                           'malformed price when convertOdds called \033[0m')
            # Update price in place
            runner['price'] = final

        return marketDic


# TakeFirst actually a class not a func
# so needs instantiating, and then take_first(..)
# runs the call method of the class
take_first = TakeFirst()
strip_odds = StripOdds()
strip_mkt_name = StripMarketName()
convert_odds = ConvertOdds()
format_runners = FormatRunners()


class EventLoader(ItemLoader):

    # used if fields don't specify one
    default_input_processor = Strip()
    default_output_processor = TakeFirst()

    teams_in = MapCompose(unicode.strip, unicode.title)
    teams_out = Identity()  # don't apply default

    dateTime_in = Compose(take_first, parse_str2date, parse_date2str)
    # dateTime_out = MapCompose(parse_date2str)

    markets_in = MapCompose(strip_mkt_name, strip_odds, convert_odds, format_runners)
    markets_out = Identity()  # don't apply default
