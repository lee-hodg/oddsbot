import psycopg2

conn = psycopg2.connect("dbname=arbs user=oddsbot password='oddsbot' host=localhost")
with conn:
    cur = conn.cursor()
    # Create some test tables for practice on
    # initSQLcmd = "CREATE TABLE test_tab(Id SERIAL PRIMARY KEY, team1 TEXT, team2 TEXT, bookie_name TEXT, bookie_odd REAL)"
    # insSQLcmd = "INSERT INTO test_tab(team1, team2, bookie_name, bookie_odd) VALUES (%s, %s, %s, %s)"
    # xinitSQLcmd = "CREATE TABLE xtest_tab(Id SERIAL PRIMARY KEY, team1 TEXT, team2 TEXT, bookie_name TEXT, bookie_odd REAL)"
    # xinsSQLcmd = "INSERT INTO xtest_tab(team1, team2, bookie_name, bookie_odd) VALUES (%s, %s, %s, %s)"
    # cur.execute(initSQLcmd)
    # cur.execute(xinitSQLcmd)
    # Add some data or easily do this via pgadminIII say
    # cur.execute(xinsSQLcmd, ('Man U', 'Everton', 'Coral', 1.4))
    # cur.execute(xinsSQLcmd, ('Man U', 'Everton', 'Betfair', 1.1))
    # Do the join selection
    selSQLcmd = 'SELECT * FROM test_tab, xtest_tab WHERE test_tab.team1=xtest_tab.team1;'
    cur.execute(selSQLcmd)
    cur.fetchone()

# In ipython I think conn.commit() was needed and in pgadminIII refresh (when db
# highlighted not table)

# Apparentely unless the func can be implemented with SQL
# it can't be run, so this way we could run strCmp
# (Maybe you think something like SELECT * FROM table1, table2 WHERE %(return)s'
# %  myfunc(), but then how do you get table1.team1, table2.team1 to the python
# func? etc, impossible. You could decide you use a dictionary on every single
# name before writing to postgres, and do away with strCmp but then with the
# dict of team names, strCmp would be fast anyway instantly returning, plus lose
# all benefits of strCmp. No go.
# You could use PL/Python:
# http://www.postgresql.org/docs/9.0/static/plpython-funcs.html
# Looks like you can do imports with some trick
# http://stackoverflow.com/questions/15023080/how-are-import-statements-in-plpython-handled
# worth a try. Could still be slow ultimately though...
