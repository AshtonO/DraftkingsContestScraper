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

def insertContest(contest_id, name, sport, status, date, total_prizes, max_entries, entries, entry_fee, is_guaranteed):
    print 'contest_id: ', contest_id, 'name: ' , name, 'sport: ', sport, 'status: ' , status , ' date: ', date , ' total_prizes ', total_prizes, 'max_entries: ', max_entries, ' entries: ', entries, ' entry_fee: ', entry_fee, ' is guaranteed: ', is_guaranteed
    data =(contest_id, str(name), str(sport), str(status), str(date), total_prizes, max_entries, entries, entry_fee, str(is_guaranteed))
    insertCommand = ("INSERT IGNORE INTO contests(contest_id, name, sport, status, date, total_prizes, "
                    "max_entries, entries, entry_fee, is_guaranteed) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
    
    cursor.execute(insertCommand, data)
    connection.commit()   


    
def createTables(cursor):
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

def createDatabase():
    try:
        connection = mysql.connector.connect(user = globalVariables.DATABASE_USER)
        cursor = connection.cursor()
        command = "CREATE DATABASE %s" % globalVariables.DATABASE_NAME
        cursor.execute(command)
        print 'Successfully created the database'
    except mysql.connector.Error as err:
        print "Failed creating database: %s" % err



def initConnection():
    return mysql.connector.connect(user=globalVariables.DATABASE_USER, password=globalVariables.DATABASE_PASSWORD,
                                database=globalVariables.DATABASE_NAME)


def initCursor():
    return connection.cursor()


#initialize a connection to the databasetry:
try:
    connection = initConnection()
    cursor = initCursor()
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
        createDatabase()

        #if successful, try to init again
        connection = initConnection()
        cursor = initCursor()
    else:
        print(err)

if __name__ == "__main__":
    createTables(cursor)
 
