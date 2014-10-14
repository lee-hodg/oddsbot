import datetime


class Arb:

    #
    # Class to represent an arb.
    # As well as a str method to print the Arb
    # We will have an SQL write method,
    # and a get value method
    #

    def __init__(self, when, sport, market_type, competition, name,
                 bet_on, bookie, bookie_price, exchange, mid, exchange_price1,
                 exchange_stake1, exchange_price2, exchange_stake2,
                 exchange_stake3, exchange_price3):
        self.when = when
        self.sport = sport
        self.market_type = market_type
        self.competition = competition
        self.event_name = name
        self.bet_on = bet_on
        self.bookie = bookie
        self.bookie_price = bookie_price
        self.exchange = exchange
        self.mid = mid  # to form link to event on exch
        self.exchange_price1 = exchange_price1
        self.exchange_stake1 = exchange_stake1
        self.exchange_price2 = exchange_price2
        self.exchange_stake2 = exchange_stake2
        self.exchange_price3 = exchange_price3
        self.exchange_stake3 = exchange_stake3
        # self.found_stamp = datetime.datetime.now(pytz.timezone('Europe/London')).strftime('%Y-%m-%d %H:%M')
        # Django  wants YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ] format.
        # Even setting Europe/London, without inc the TZ in formatting
        # (UTC+1:00 etc), which might make daylight savint time a headache,
        # Django will still assume this string is UTC time, so just give it UTC time.
        # then it will manage it correctly.
        self.found_stamp = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')

    #
    # Arb worth if matched it out, as percentage
    #
    # c is commission as decimal, e.g. 5% =0.05
    def getValue(self, c=0.05):
        bstake = 100
        breturn = self.bookie_price*bstake
        netbreturn = (self.bookie_price-1)*bstake

        lstake = (breturn)/(self.exchange_price1-c)
        liability = lstake*(self.exchange_price1-1)

        backprofit = netbreturn-liability
        # layprofit = (1-c)*lstake-bstake

        ValPercentage = (backprofit/bstake)*100
        return "%.2f" % ValPercentage

    def __str__(self):
        # string returns bytes (encoded)
        output = u'\033[7m Arb info \033[0m: \n\n'
        output += u'Event date and time = %s \n' % self.when
        output += u'Sport = %s \n' % self.sport
        output += u'Market type = %s \n' % self.market_type
        output += u'Competition = %s \n' % self.competition
        output += u'Event Name = %s \n' % self.event_name
        output += u'Bet on = %s \n' % self.bet_on
        output += u'Arb Value at c:0.05 = %s \n' % self.getValue()
        output += u'Bookie = %s \n' % self.bookie
        output += u'Bookie Odds = %s \n' % self.bookie_price
        output += u'Exchange = %s \n' % self.exchange
        output += u'Market id = %s \n' % self.mid
        output += u'Exchange Odds1 = %s \n' % self.exchange_price1
        output += u'Exchange Stake1 = %s \n' % self.exchange_stake1
        output += u'Exchange Odds2 = %s \n' % self.exchange_price2
        output += u'Exchange Stake2 = %s \n' % self.exchange_stake2
        output += u'Exchange Odds3 = %s \n' % self.exchange_price3
        output += u'Exchange Stake3 = %s \n' % self.exchange_stake3
        output += u'Found at = %s \n' % self.found_stamp
        return output.encode('utf-8')   # str(..) on unicode obj needs encoding

    def writeSQLarb(self, conn, comm=0.05):
        values_to_insert = (self.when,
                            self.sport,
                            self.market_type,
                            self.competition,
                            self.event_name,
                            self.bet_on,
                            self.getValue(comm),
                            self.bookie,
                            self.bookie_price,
                            self.exchange,
                            self.mid,
                            self.exchange_price1,
                            self.exchange_stake1,
                            self.exchange_price2,
                            self.exchange_stake2,
                            self.exchange_price3,
                            self.exchange_stake3,
                            self.found_stamp
                            )
        with conn:
            cur = conn.cursor()
            insSQLcmd = "INSERT INTO "
            insSQLcmd += "arbs_tab(event_datetime, sport, market_type, competition, event_name, bet_on, arb_value, "
            insSQLcmd += "bookie_name, bookie_odd, exchange_name, mid, exchange_odd1, exchange_stake1, "
            insSQLcmd += "exchange_odd2, exchange_stake2, exchange_odd3, exchange_stake3, found_stamp) "
            insSQLcmd += "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING Id"
            try:
                cur.execute(insSQLcmd, values_to_insert)
            except Exception:
                log.error(e)
            # Get row id of last row this cur inserted
            # print 'ID of item inserted: %s' %  cur.lastrowid
            return cur.fetchone()[0]
