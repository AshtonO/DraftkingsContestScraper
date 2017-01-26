import globalVariables
import mysql.connector
from mysql.connector import errorcode
import time

TABLES = {}
TABLES['contests'] = (
    "CREATE TABLE contests ("
    " contest_id int NOT NULL UNIQUE,"
    " draftGroupID int, "
    " name varchar(500) NOT NULL,"
    " sport varchar(50) NOT NULL,"
    " status varchar(50) NOT NULL,"
    " date varchar(50) NOT NULL,"
    " total_prizes double NOT NULL,"
    " max_entries double NOT NULL,"
    " entries double NOT NULL, "
    " entry_fee double, "
    " positions_paid double, " 
    " money_line double,"
    " is_guaranteed varchar (10)"
    ")")

TABLES['contestResults'] = (
    "CREATE TABLE contestResults ("
    " contest_id int NOT NULL,"
    " place double NOT NULL,"
    " contestant_name varchar(500) NOT NULL,"
    " points double NOT NULL, "
    " entry_fee double, "
    " winning double NOT NULL, "
    " c1 varchar(100),"
    " c2 varchar(100),"
    " w1 varchar(100),"
    " w2 varchar(100),"
    " w3 varchar(100),"
    " d1 varchar(100),"
    " d2 varchar(100),"
    " g varchar(100),"
    " u varchar(100),"
    " primary key(contest_id, contestant_name)"
    ")")

# search through the contests that we have that still need results.
# return their contest_id and dates in a list
def get_contests_that_need_results():
    currentDate = time.strftime("%Y-%m-%d")
    cursor.execute("Select contest_id, date from contests where (status != 'RESULTS_GATHERED' and status != 'TOO_OLD' and date not like '%s') OR (status = 'RESULTS_GATHERED' AND  entry_fee is NULL)", str(currentDate))
    contests = []
    for contest_id,date in cursor:
        contests.append([contest_id, date])
    return contests


# updates the status for all contests on the given date to be TOO_OLD (this usually happens when we wait too long to gather results and
# draftkings take them down) 
def date_too_old(date):
    command = "Update contests set status = 'TOO_OLD' where date like '%s'"%date 
    cursor.execute(command)
    connection.commit()


# check and see if we've already gathered contests for today's date
def have_gathered_todays_contests():
    currentDate = time.strftime("%Y-%m-%d")
    command = "Select distinct date from contests"
    cursor.execute(command)
    found = False
    for date in cursor:
        if(str(date[0]) == str(currentDate)):
            print 'We\'ve already gathered contests for todays date: %s' % str(date[0])
            found = True
    if not found:
        print 'We haven\'t gathered results for todays date: %s' % str(currentDate[0])
    return found


def insert_contest(contest_id, name, sport, status, date, total_prizes, max_entries, entries, entry_fee, is_guaranteed):
    print 'contest_id: ', contest_id, 'name: ' , name, 'sport: ', sport, 'status: ' , status , ' date: ', date , ' total_prizes ', total_prizes, 'max_entries: ', max_entries, ' entries: ', entries, ' entry_fee: ', entry_fee, ' is guaranteed: ', is_guaranteed
    data =(contest_id, str(name), str(sport), str(status), str(date), total_prizes, max_entries, entries, entry_fee, str(is_guaranteed))
    insertCommand = ("INSERT IGNORE INTO contests(contest_id, name, sport, status, date, total_prizes, "
                    "max_entries, entries, entry_fee, is_guaranteed) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
    
    cursor.execute(insertCommand, data)
    connection.commit()   


def update_contest_results(contest_id, status, draftGroupID, positions_paid, money_line, results):
    cursor.execute("UPDATE contests set status = %s, draftGroupID= %s, positions_paid = %s, money_line = %s where contest_id = %s", ('RESULTS_GATHERED', draftGroupID, str(positions_paid), str(money_line), str(contest_id)))

    for r in results:
        if r['payout'] >= 0:
            if not isinstance( r['payout'], ( int, long ) ):
                if( '$' in r['payout']):
                    r['payout'] = r['payout'].replace('$', '')
                if( ',' in r['payout']):
                    r['payout'] = r['payout'].replace(',', '')

            cursor.execute("insert ignore into contestResults(contest_id, place, contestant_name, points, winning, c1, c2, w1, w2, w3, d1, d2, g, u) "
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", ((contest_id, r['place'], r['name'], r['points'], r['payout'],
                                                                                    r['lineup'][0], r['lineup'][1], r['lineup'][2], r['lineup'][3],
                                                                                    r['lineup'][4], r['lineup'][5], r['lineup'][6], r['lineup'][7],
                                                                                    r['lineup'][8]))) 
    connection.commit()


def cancel_contest(contest_id):
    command = "DELETE FROM contests where contest_id = %s" % contest_id
    print command
    cursor.execute(command)
    connection.commit()
    print 'Deleting contest %s because it was cancelled or not found' % contest_id


def create_table(cursor):
    for name, ddl in TABLES.iteritems():
        try:
            print("Creating table {}:", name);
    	    cursor.execute(ddl)
        except mysql.connector.Error as err:
    	    if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
    	        print("already exists.")
    	    else:
    	        print(err.msg)
        else:
            print("OK")


def create_database():
    try:
        connection = mysql.connector.connect(user = globalVariables.DATABASE_USER)
        cursor = connection.cursor()
        command = "CREATE DATABASE %s" % globalVariables.DATABASE_NAME
        cursor.execute(command)
        print 'Successfully created the database'
    except mysql.connector.Error as err:
        print "Failed creating database: %s" % err


def init_connection():
    return mysql.connector.connect(user=globalVariables.DATABASE_USER, password=globalVariables.DATABASE_PASSWORD,
                                database=globalVariables.DATABASE_NAME)


def init_cursor():
    return connection.cursor()


#initialize a connection to the databasetry:
try:
    connection = init_connection()
    cursor = init_cursor()
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
        create_database()

        #if successful, try to init again
        connection = init_connection()
        cursor = init_cursor()
    else:
        print(err)

if __name__ == "__main__":
    create_tables(cursor)
 
