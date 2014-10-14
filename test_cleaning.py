#!/home/lee/ENV/bin/python
# -*- coding: utf-8 -*-
from __future__ import division #nice division
import json
import difflib #for string comparison
import sqlite3 as lite #for arbs sqlite db
import sys, os
import cleaner
from arb import Arb
import datetime


###################################clean JSON database first###################################
dirname="JSONdata"
print '\033[7m CLEANING dir:', dirname,'.... \033[0m'
#read in .bjson(Bookie), .xjson(Exchange) files in JSONdata dir
JSONfiles = []
for filename in os.listdir(dirname):
    fileJSON = None
    if filename.endswith(".bjson"):
        #bookie db
        print 'Clean bookie file:', filename
        with open(dirname+'/'+filename,'r') as file:
            try:
                fileJSON=json.load(file)
            except ValueError as e:
                print '[Cleaning err:] %s' % e
                print '[Cleaning err:] is the file %s valid JSON?' % filename
                continue
            for jitem in fileJSON:
                cleaner.rinseNclean(jitem)
                cleaner.splitTeams(jitem)
                cleaner.convertOdds(jitem)
    elif filename.endswith(".xjson"):
        #exchange db, don't convertOddds, use Ex version of rNc
        print 'Clean exchange file:', filename
        with open(dirname+'/'+filename,'r') as file:
            fileJSON=json.load(file)
            for jitem in fileJSON:
                cleaner.rinseNclean(jitem, exchange=True)
                cleaner.splitTeams(jitem)
    if fileJSON:
        with open(dirname+'/'+filename+'.clean','w') as cfile:
            json.dump(fileJSON, cfile, indent=4)
##############################################################################################  
