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
