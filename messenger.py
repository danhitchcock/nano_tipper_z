import praw
import time
from datetime import datetime
from time import sleep
import mysql.connector
# access the sql library
with open('sql_password') as f:
    sql_password = f.read()
mydb = mysql.connector.connect(user='root', password=sql_password,
                              host='localhost',
                              auth_plugin='mysql_native_password', database='nano_tipper_z')
mycursor = mydb.cursor()

reddit = praw.Reddit('bot1')

while True:
    sql = "SELECT * FROM messages"
    mycursor.execute(sql)
    results = mycursor.fetchall()
    mydb.commit()
    for result in results:
        print(time.strftime('%Y-%m-%d %H:%M:%S'), result[1], result[2], repr(result[3]))
        # send the message
        reddit.redditor(str(result[1])).message(str(result[2]), str(result[3]))
        sql = "DELETE FROM messages WHERE id = %s"
        val = (result[0], )
        mycursor.execute(sql, val)
        mydb.commit()

    sleep(6)
