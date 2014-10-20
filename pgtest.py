#!/usr/bin/env python
import datetime
# Aim of this is to push to MO test data from mongo db
# to postgres for the purposes of comparing the speed of
# arb finding via a join.

# =============MONGO
# Now can easily insert documents with xmarket_id = xmarkets.insert(someevent)
# (see http://api.mongodb.org/python/current/tutorial.html)
from pymongo import MongoClient
client = MongoClient()
client = MongoClient('localhost', 27017)
db = client.oddsbot_scrapy  # connect to our db
events = db.events  # then bookies events collection
xevents = db.xevents  # then exchange events collection
# arbs = db.arbs  # arbs collection

# =============POSTGRES (store arbs in postgres)
import psycopg2
conn = psycopg2.connect("dbname=arbs user=oddsbot password='oddsbot' host=localhost")
with conn:
    cur = conn.cursor()
    initSQLcmd = ("CREATE TABLE IF NOT EXISTS "
                  "test_tab(Id SERIAL PRIMARY KEY,"
                  "event_datetime TEXT,"
                  "sport TEXT, market_type TEXT, bookie_name TEXT,"
                  "competition TEXT, event_name TEXT, team1 TEXT, team2 TEXT,"
                  "rname1 TEXT, rprice1 REAL,"
                  "rname2 TEXT, rprice2 REAL,"
                  "rname3 TEXT, rprice3 REAL)"
                  )
    cur.execute(initSQLcmd)
    xinitSQLcmd = ("CREATE TABLE IF NOT EXISTS "
                   "xtest_tab(Id SERIAL PRIMARY KEY,"
                   "event_datetime TEXT,"
                   "sport TEXT, market_type TEXT, bookie_name TEXT,"
                   "competition TEXT, event_name TEXT, team1 TEXT, team2 TEXT,"
                   "rname1 TEXT, rprice1 REAL, rstake1 REAL,"
                   "rname2 TEXT, rprice2 REAL, rstake2 REAL,"
                   "rname3 TEXT, rprice3 REAL, rstake3 REAL)"
                   )
    cur.execute(xinitSQLcmd)

# Now throw mongo MO data into pgdb

with conn:
    cur = conn.cursor()
    insSQLcmd = ("INSERT INTO "
                 "test_tab("
                 "event_datetime,"
                 "sport, market_type, bookie_name,"
                 "team1, team2,"
                 "rname1, rprice1,"
                 "rname2, rprice2,"
                 "rname3, rprice3)"
                 " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                 )
    xinsSQLcmd = ("INSERT INTO "
                  "xtest_tab("
                  "event_datetime,"
                  "market_type, bookie_name,"
                  "team1, team2,"
                  "rname1, rprice1, rstake1,"
                  "rname2, rprice2, rstake2,"
                  "rname3, rprice3, rstake3)"
                  " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                  )
    for event in events.find():
        sdt = event['dateTime']
        # dt = datetime.datetime.strptime(sdt, '%m %d').replace(year=datetime.datetime.now().year)
        # event_datetime = dt.strftime('%Y %m %d')
        sport = event['sport']
        bookie_name = event['bookie']
        team1 = event['teams'][0]
        team2 = event['teams'][1]
        MOmarket = [market for market in event['markets']
                    if market['marketName'] == 'Match Odds']

        if MOmarket:
            MOmarket = MOmarket[0]
            market_name = MOmarket['marketName']
            runners = MOmarket['runners']
            if runners:
                rname1 = runners[0]['runnerName']
                rprice1 = runners[0]['price']
                rname2 = runners[1]['runnerName']
                rprice2 = runners[1]['price']
                rname3 = runners[2]['runnerName']
                rprice3 = runners[2]['price']
        values_to_insert = (sdt, sport, market_name,
                            bookie_name, team1, team2,
                            rname1, rprice1,
                            rname2, rprice2,
                            rname3, rprice3)

        try:
            cur.execute(insSQLcmd, values_to_insert)
        except Exception as e:
            print e
            print values_to_insert
            exit()

    for event in xevents.find():
        sdt = event['shortDateTime']
        # dt = datetime.datetime.strptime(sdt, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d')
        bookie_name = event['exchangeName']
        team1 = event['team1']
        team2 = event['team2']
        MOmarket = [market for market in event['markets']
                    if market['marketName'] == 'Match Odds']

        try:
            if MOmarket:
                MOmarket = MOmarket[0]
                market_name = MOmarket['marketName']
                runners = MOmarket['runners']
                rname1 = rstake1 = rname2 = rstake2 = rname3 = rstake3 = 0
                if runners:
                    rname1 = runners[0]['runnerName']
                    a2L1 = runners[0]['availableToLay']
                    if a2L1:
                        rprice1 = a2L1[0]['price']
                        rstake1 = a2L1[0]['size']
                    rname2 = runners[1]['runnerName']
                    a2L2 = runners[1]['availableToLay']
                    if a2L2:
                        rprice2 = a2L2[0]['price']
                        rstake2 = a2L2[0]['size']
                    rname3 = runners[2]['runnerName']
                    a2L3 = runners[2]['availableToLay']
                    if a2L3:
                        rprice3 = a2L3[0]['price']
                        rstake3 = a2L3[0]['size']

            xvalues_to_insert = (sdt, market_name,
                                bookie_name, team1, team2,
                                rname1, rprice1, rstake1,
                                rname2, rprice2, rstake2,
                                rname3, rprice3, rstake3)

            try:
                cur.execute(xinsSQLcmd, xvalues_to_insert)
            except Exception as e:
                print e
                print values_to_insert
                exit()
        except IndexError:
            print event
            pass
