# Installing

## Make the virtualenv as normal

    virtualenv venv --no-site-packages
    source venv/bin/activate

Note `libxml` library is required to be installed. Running

    sudo apt-get install libxslt1-dev libxslt1.1 libxml2-dev libxml2 libssl-dev

was sufficient.

Next install with 

    pip install Scrapy

or if using `requirements.txt`:

    pip install -r requirements.txt

## Make sure mongodb is installed

See [install mongodb](http://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/)
for details.

You can also just store as JSON if you like by using the JSON exporter

     scrapy crawl Betredkings -o 'JSONdata/Betredkings.bjson' -t json

for example.

Make sure the `mongod` (daemon) is running with `sudo service mongod status`, then use
the client `mongo` to investigate. E.g `shows dbs` lists the databases, `use bookie_scrape` switches
to that database and `db` confirms. Take a look at the [docs](http://docs.mongodb.org/manual/core/introduction/)
for more.



#A VERY USEFUL EXPRESSION TO MAKE BATCH REPLACEMENTS

    find . -name '*.py' | xargs sed -i "s/'\/home\/lee\/oddScr\/logs'/settings\['LOG_DIR'\]/g"

NOTE: no escaping of single quotes needed when using double quotes around whole replace string.

## Insert text at top of all files that contain LOG_DIR

    grep -rl "LOG_DIR" . | xargs sed -i -e '1ifrom scrapy.conf import settings\'

## Cron job (leave blank line at bottom of file, set this with crontab -e)

E.g. every 4hrs between 10am and 10pm:

    0 10-22/4 * * * /bin/sh /home/lee/oddsScr/autoscrapy.sh > /home/lee/cron_scrape.log

# Postgres functions support with plpython

First install `sudo apt-get install postgresql-plpython`

Then `sudo su postgres`, `psql arbs`, `CREATE PROCEDURAL LANGUAGE 'plpythonu' HANDLER plpython_call_handler;`

Then create a simple function like (make sure connect to correct db otherwise plpython not installed on others)

    CREATE FUNCTION cmpStr (team1 text, team2 text)
        RETURNS boolean
    AS $$
      if team1 == team2:
          return True
      else:
          return False
    $$ LANGUAGE plpythonu;

and verify it works like `SELECT cmpStr('Liverpool', 'Liverpool');`


    CREATE FUNCTION cmpStr (team1 text, team2 text)
        RETURNS boolean
    AS $$
         if 'compStr' in SD:
              compStr = SD['compStr']
          else:
              from findarbs import cmpStr
              SD['compStr'] = cmpStr
          return compStr(team1, team2)
    $$ LANGUAGE plpythonu;

My main problem now is working out how to get the pythonpath right, so compare module with compStr can be imported
the following

          if 'path' in SD:
          path = SD['path']
      else:
          from sys import path
              SD['path'] = path
          path.append('/home/lee/Desktop/pyco/oddsScr_v2/Bookies/')

          if 'compStr' in SD:
              compStr = SD['compStr']
          else:
              from compare import compStr
              SD['compStr'] = compStr
          return compStr(team1, team2)
       
still doesn't work. Unless put compare module in say `/usr/lib/python2.7/dist-packages` then no problems with the `SELECT cmpStr('Liverpool', 'Liverpool');`
This is just a minor thing anyway, and for testing leaving it in the sys dir isn't a big deal, if it goes to production, can figure out the PYTHONPATH stuff then.

Now 

    SELECT * FROM test_tab, xtest_tab WHERE cmpStr(test_tab.team1, xtest_tab.team1) and test_tab.bookie_odd>xtest_tab.bookie;

works.

It's still to be seen if this would be faster than the normal findarbs script, the final obstacle is how to record
data from bookies and exchanges in a relational db given how dirty it can be.

I get before doing that, a good speed test might be to make a simple db structure for MO markets storing, then write a small
python script to push all the mongo data relevant into the postgres test db (for bookie and exchange), then try and have it find some arbs and compare the speeds I get out. If it's just as slow forget it, if it is vastly quicker, I might have to think harder.

SELECT test_tab.team1, test_tab.team2, test_tab.bookie_name, xtest_tab.bookie_name FROM test_tab INNER JOIN xtest_tab ON cmpStr(test_tab.team1, xtest_tab.team1) and compStr(test_tab.team2, xtest_tab.team2);

NB without the compStr func the join is almost instant, with that it slows down somewhat.

The tests showed that finarbs was actually faster for some reason when cmpStr was used in postgres. So I don't think the JOIN is going to help us here.

# Timings and groupings
