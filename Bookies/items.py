# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field
# from collections import defaultdict


class EventItem(Item):
    # define the fields for your item here like:
    # name = Field()
    eventDate = Field()
    eventTime = Field()
    eventName = Field()
    odd1 = Field()
    odd2 = Field()
    odd3 = Field()


class EventItem2(Item):
    '''
    Store list of market dictionaries in markets.
    Each has marketName (e.g. 'CS') and  runners field,
    which is in turn a list of dictionaries consiting
    of runnerName and price.

    Teams also a list of teams
    '''
    sport = Field(default='Soccer')
    markets = Field()
    bookie = Field()
    dateTime = Field()
    teams = Field()


# class FlexEventItem(Item):
#     '''
#     Item that allows fields to be added
#     flexibly, i.e. even if field not predefined
#     (variable number of odds) say, we can add that
#     extra field at runtime.
#     Another option would just to make a oddsList = Field()
#     then in the scraper oddsList = [], of which you then append.
#     '''
#     sport = Field(default='Soccer')
#     market = Field(default='Match Odds')
#     bookie = Field()
#     eventDate = Field()
#     eventTime = Field()
#     eventName = Field()
#
#     def __setitem__(self, key, value):
#         # Instead of throwing exception create field
#         # and set its value if field starts with 'odd'
#         # this way we get dynamic number of odds fields.
#         if key not in self.fields:
#             if key.startswith('odd'):
#                 self.fields[key] = Field()
#             else:
#                 raise KeyError("%s does not support field: %s" %
#                                (self.__class__.__name__, key))
#
#         self._values[key] = value


# class FlexEventItem(Item):
#     '''
#     Item that allows fields to be added
#     flexibly, i.e. even if field not predefined
#     (variable number of odds) say, we can add that
#     extra field at runtime.
#
#     '''
#     fields = defaultdict(lambda: Field())
