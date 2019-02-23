from time import sleep

import mysql.connector
import praw

# access the sql library
with open('sql_password.txt') as f:
    sql_password = f.read()
mydb = mysql.connector.connect(user='root', password=sql_password,
                               host='localhost',
                               auth_plugin='mysql_native_password', database='nano_tipper_z')
mycursor = mydb.cursor()

# initiate the bot and all friendly subreddits
reddit = praw.Reddit('bot1')

while True:
    sql = "SELECT * FROM messages"
    mycursor.execute(sql)
    results = mycursor.fetchall()
    mydb.commit()
    for result in results:
        print(result)
        sql = "DELETE FROM messages WHERE id = %s"
        val = (result[0],)
        mycursor.execute(sql, val)
        # pretend to be a message being sent
        sleep(2)
        mydb.commit()
    sleep(6)
