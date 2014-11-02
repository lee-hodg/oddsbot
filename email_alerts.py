# #!/usr/bin/env python
# Django and oddsbot
from scrapy.conf import settings
import sys
import os
sys.path.insert(1, settings['ODDSBOT_DIR'])
sys.path.insert(1, settings['ODDSBOT_ENV'])
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oddsbot.settings")

from arbs.models import Arb
from arbs.filters import ArbFilter
# from accounts.models import UserProfile
from django.utils import timezone
# import pytz
import datetime
from django.http import QueryDict
# from django.utils.datastructures import MultiValueDictKeyError
from decimal import *


# def parse_eventdt(lower, upper):
#     #
#     # js eventdt slider will produce values as follows
#     # 0: now, 1: 1h, 2: 2h, 3: 24h, 4: 3days, 5: 1wk, 6:2wk, 7: 1m+
#     # We need to parse these into appropriate datetime objects to filter on.
#     # N.B. we use timezone because we need 'timezone aware' datetime, however,
#     # regardless of settings.py this always gives UTC, we convert to tz
#     # matching our settings.py (Europe/London, with dst accounted for) with
#     # localtime.
#     #
#     now = timezone.localtime(timezone.now())
#     h1 = now + datetime.timedelta(hours=1)
#     h2 = now + datetime.timedelta(hours=2)
#     h24 = now + datetime.timedelta(days=1)
#     days3 = now + datetime.timedelta(days=3)
#     wk1 = now + datetime.timedelta(weeks=1)
#     wk2 = now + datetime.timedelta(weeks=2)
#     mp = now+datetime.timedelta(weeks=520)  # ten years in future should suffice!
#     dateDict = {'0': now, '1': h1, '2': h2, '3': h24, '4': days3,
#                 '5': wk1, '6': wk2, '7': mp}
#     return (dateDict[lower], dateDict[upper])


def filterArbs(user, GETstr, arbids=[]):
    '''
    When passed a user along with a GETstr (of the form
    the ArbFilter from the OddsBot table head produces), this
    function filters Arbs from the db that match the params.

    Optional: if arbids (e.g could be just a single arb)
    is passed, this should be used instead of
    Arb.objects.filter(event_datetime__gt=now).
    '''

    comms = {'Betfair': 5, 'Betdaq': 5, 'Smarkets': 5, 'WBX': 5}  # default comm
    now = timezone.localtime(timezone.now())
    mp = now+datetime.timedelta(weeks=520)  # ten years in future
    # Only offer email alerts for premium members, so base queryset is all
    # future arbs.
    if not arbids:
        queryset = Arb.objects.filter(event_datetime__gt=now)
    else:
        # If list of arbids passed, use these to form
        # initial queryset instead.
        queryset = Arb.objects.filter(pk__in=arbids)

    # Set comms for user
    comms['Betfair'] = float(user.userprofile.betfair_comm)
    comms['Betdaq'] = float(user.userprofile.betdaq_comm)
    comms['Smarkets'] = float(user.userprofile.smarkets_comm)
    comms['WBX'] = float(user.userprofile.wbx_comm)

    #  Make a genuine QueryDict from the GETstr. Usually immutable.
    GET = QueryDict(GETstr, mutable=True)

    # Deal with the daterange first.
    # First parse lower and upper event_datetime filter vals,
    # and reduce queryset accordingingly.Recall popping removes from GET.
    try:
        # We try/except since sometimes there will be a GET request (like sort)
        # for which these values are not defined.
        # Pop as we don't want to pass to ArbFilter query
        prsd_eventdt0 = GET.pop('event_datetime_0', [now])[0]  # def now
        prsd_eventdt1 = GET.pop('event_datetime_1', [mp])[0]  # def 10yr in fut
        # update queryset with dt filtered.
        queryset = queryset.filter(event_datetime__range=(prsd_eventdt0, prsd_eventdt1))
    except MultiValueDictKeyError as e:
        print '[OddsBot Error]: MVD KeyError when reaping eventdates from request.GET: %s' % e

    # Filter on ROI lastly, so we can use custom comms
    try:
        arb_value_0 = Decimal(GET.pop('arb_value_0', ['-10'])[0])
        arb_value_1 = Decimal(GET.pop('arb_value_1', ['20'])[0])
    except InvalidOperation:
        # Not valid decimals
        arb_value_0 = Decimal(-10)
        arb_value_1 = Decimal(20)

    # Now with remainder of GET request construct the filter.
    f = ArbFilter(GET, queryset)

    if f.form.is_valid():
        # List of arbs returned
        list = [arbobj for arbobj in f]
    else:
        # form not valid; gather errors for ajax
        list = []
        # errors = f.form.errors

    # Now set custom comm per arb.
    for arb in list:
        if arb.exchange_name == 'Betfair':
            arb.comms['Betfair'] = comms['Betfair']
        elif arb.exchange_name == 'Betdaq':
            arb.comms['Betdaq'] = comms['Betdaq']
        elif arb.exchange_name == 'Smarkets':
            arb.comms['Smarkets'] = comms['Smarkets']
        elif arb.exchange_name == 'WBX':
            arb.comms['WBX'] = comms['WBX']

    # With the custom comms set now perform ROI filter
    list = [arb for arb in list if (arb.custom_arb_value() >= arb_value_0 and
            arb.custom_arb_value() <= arb_value_1)]

    # Sort the arbs by the custom ROI
    list = sorted(list, key=lambda a: -a.custom_arb_value())

    return list
