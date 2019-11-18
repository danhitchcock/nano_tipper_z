import praw
from praw.exceptions import APIException
import time

from time import sleep
import mysql.connector
import configparser

config = configparser.ConfigParser()
config.read('./tipper.ini')
# config.sections()
sql_password = config['SQL']['sql_password']
database_name = config['SQL']['database_name']
tip_bot_on = config['BOT']['tip_bot_on']
tip_bot_username = config['BOT']['tip_bot_username']
program_minimum = float(config['BOT']['program_minimum'])

mydb = mysql.connector.connect(user='root', password=sql_password,
                              host='localhost',
                              auth_plugin='mysql_native_password', database=database_name)
mycursor = mydb.cursor()

reddit = praw.Reddit('bot1')

while True:
    sql = "SELECT * FROM messages"
    mycursor.execute(sql)
    results = mycursor.fetchall()
    mydb.commit()
    for result in results:
        print(time.strftime('%Y-%m-%d %H:%M:%S'), result[1], result[2], repr(result[3])[:50])
        # send the message
        try:
            reddit.redditor(str(result[1])).message(str(result[2]), str(result[3]))
        except:
            pass
        sql = "DELETE FROM messages WHERE id = %s"
        val = (result[0], )
        mycursor.execute(sql, val)
        mydb.commit()

    sleep(6)
