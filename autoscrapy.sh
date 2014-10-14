#!/bin/sh

# run spiders here using scrapy cmd line
# I don't see any reason to bother running
# scrapy from python?

# for cron
PATH=$PATH:/usr/local/bin
export PATH

# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")
echo "Script dir:"
echo $SCRIPTPATH

cd $SCRIPTPATH

rm log/*

rm JSONdata/* #imp to remove all.
echo "Begginning scrape of exchanges"
cd Exchanges; python BFscrapev2.py; cd ..
echo "Beginning bookies scraping session"
scrapy crawl Teambet -o 'JSONdata/Teambet.bjson' -t json
scrapy crawl Skybet -o 'JSONdata/Skybet.bjson' -t json
scrapy crawl Betinternet -o 'JSONdata/Betinternet.bjson' -t json
scrapy crawl Dhoze -o 'JSONdata/Dhoze.bjson' -t json
scrapy crawl Jetbull -o 'JSONdata/Jetbull.bjson' -t json
scrapy crawl Betredkings -o 'JSONdata/Betredkings.bjson' -t json
scrapy crawl Guts -o 'JSONdata/Guts.bjson' -t json
scrapy crawl Betfred -o 'JSONdata/Betfred.bjson' -t json
scrapy crawl Boylesports -o 'JSONdata/Boylesports.bjson' -t json
echo "Commence arb hunt"
python findarbs.py

rm JSONdata/* #imp to remove all.
echo "Begginning scrape of exchanges"
cd Exchanges; python BFscrapev2.py; cd ..
echo "Beginning bookies scraping session"
#scrapy crawl Bets777 -o 'JSONdata/Bets777.bjson' -t json #closed down?
scrapy crawl Onevice -o 'JSONdata/Onevice.bjson' -t json  # good
# 888 Blocked ip? working min curl from laptop gives 410 on vpn :(
# If I use a free proxy like curl -x http://202.43.188.14:8080 'https://api.kambi.com/offering/api/v2/888/group.json'
# I get a response, but without I get 410. Why did they block my ip?
# scrapy crawl sport889 -o 'JSONdata/sport888.bjson' -t json 
scrapy crawl Apollobet -o 'JSONdata/Apollobet.bjson' -t json #good
#Apollobet can take a while(website is very slow)
echo "Commence arb hunt"
python findarbs.py

rm JSONdata/* #imp to remove all.
echo "Begginning scrape of exchanges"
cd Exchanges; python BFscrapev2.py; cd ..
echo "Beginning bookies scraping session"
# Betsson can take 5mn (needed longer delay)
scrapy crawl Betsson -o 'JSONdata/Betsson.bjson' -t json
echo "Commence arb hunt"
python findarbs.py

# Note if ever ./autoscrapy works from shell but not cron, it could be a unicode err because
# cron redirect > to file works ok in stdout to term but not file
rm JSONdata/*
echo "Begginning re-scrape of exchanges"
cd Exchanges; python BFscrapev2.py; cd ..
#scrapy crawl Bet365 -o 'JSONdata/Bet365.bjson' -t json #I think linode, CactusVPN are blocked(see spider for more notes)
scrapy crawl Bet3000 -o 'JSONdata/Bet3000.bjson' -t json #good
# scrapy crawl Betbutler -o 'JSONdata/Betbutler.bjson' -t json  # (closed!)
scrapy crawl Betsafe -o 'JSONdata/Betsafe.bjson' -t json #good
scrapy crawl Buzzodds -o 'JSONdata/Buzzodds.bjson' -t json #good
scrapy crawl Betvictor -o 'JSONdata/Betvictor.bjson' -t json #good
scrapy crawl Coral -o 'JSONdata/Coral.bjson' -t json #good
scrapy crawl Doxxbet -o 'JSONdata/Doxxbet.bjson' -t json #good
scrapy crawl Fortunawin -o 'JSONdata/Fortunawin.bjson' -t json #good
scrapy crawl Gentingbet -o 'JSONdata/Gentingbet.bjson' -t json #good
scrapy crawl Interwetten -o 'JSONdata/Interwetten.bjson' -t json #good
# Interwetten can take a while
echo "Commence arb hunt"
python findarbs.py

rm JSONdata/*
echo "Begginning re-scrape of exchanges"
cd Exchanges; python BFscrapev2.py; cd ..
# scrapy crawl Jenningsbet -o 'JSONdata/Jenningsbet.bjson' -t json # changed platform just like Setanta (same odds so will not repeat scrape)
scrapy crawl Ladbrokes -o 'JSONdata/Ladbrokes.bjson' -t json #good
scrapy crawl Marathonbet -o 'JSONdata/Marathonbet.bjson' -t json #good
scrapy crawl Mcbookie -o 'JSONdata/Mcbookie.bjson' -t json #good
scrapy crawl Nordicbet -o 'JSONdata/Nordicbet.bjson' -t json #good
scrapy crawl Paddypower -o 'JSONdata/Paddypower.bjson' -t json #good
scrapy crawl Seaniemac -o 'JSONdata/Seaniemac.bjson' -t json #good
echo "Commence arb hunt"
python findarbs.py

rm JSONdata/*
echo "Begginning re-scrape of exchanges"
cd Exchanges; python BFscrapev2.py; cd ..
scrapy crawl Setantabet -o 'JSONdata/Setantabet.bjson' -t json #good (new site, new spider)
scrapy crawl Sportingbet -o 'JSONdata/Sportingbet.bjson' -t json #good
scrapy crawl Sportium -o 'JSONdata/Sportium.bjson' -t json #good
scrapy crawl Stanjames -o 'JSONdata/Stanjames.bjson' -t json #good
scrapy crawl Titanbet -o 'JSONdata/Titanbet.bjson' -t json #good
scrapy crawl Totesport -o 'JSONdata/Totesport.bjson' -t json #good
scrapy crawl Triobet -o 'JSONdata/Triobet.bjson' -t json #good
# scrapy crawl Unibet -o 'JSONdata/Unibet.bjson' -t json #just like 888 and paf its kambi and they blocked me (see 888)
echo "Commence arb hunt"
python findarbs.py

rm JSONdata/*
echo "Begginning re-scrape of exchanges"
cd Exchanges; python BFscrapev2.py; cd ..
scrapy crawl Williamhill -o 'JSONdata/Williamhill.bjson' -t json #good
scrapy crawl Bwin -o 'JSONdata/Bwin.bjson' -t json #good
# scrapy crawl Paf -o 'JSONdata/Paf.bjson' -t json  #just like 888 and unibet its kambi and they blocked me (see 888)
scrapy crawl Betclic -o 'JSONdata/Betclic.bjson' -t json
scrapy crawl Bet188 -o 'JSONdata/Bet188.bjson' -t json
scrapy crawl BGbet -o 'JSONdata/BGbet.bjson' -t json
scrapy crawl Betway -o 'JSONdata/Betway.bjson' -t json
scrapy crawl Whitebet -o 'JSONdata/Whitebet.bjson' -t json #good 
# scrapy crawl Heavenbet -o 'JSONdata/Heavenbet.bjson' -t json #(no longer offer sportbook 1sep14)
echo "Commence arb hunt"
python findarbs.py

rm JSONdata/*
echo "Begginning re-scrape of exchanges"
cd Exchanges; python BFscrapev2.py; cd ..
scrapy crawl Tonybet -o 'JSONdata/Tonybet.bjson' -t json #good
scrapy crawl Betathome -o 'JSONdata/Betathome.bjson' -t json  #good
scrapy crawl Oddsring -o 'JSONdata/Oddsring.bjson' -t json  #good
scrapy crawl Apostasonline -o 'JSONdata/Apostasonline.bjson' -t json  #good
echo "Commence arb hunt"
python findarbs.py
