import time

from time import sleep
from translations import mydb, mycursor, reddit

while True:
    sql = "SELECT * FROM messages"
    mycursor.execute(sql)
    results = mycursor.fetchall()
    mydb.commit()
    for result in results:
        print(
            time.strftime("%Y-%m-%d %H:%M:%S"),
            result[1],
            result[2],
            repr(result[3])[:50],
        )
        # send the message
        try:
            reddit.redditor(str(result[1])).message(str(result[2]), str(result[3]))
        except:
            pass
        sql = "DELETE FROM messages WHERE id = %s"
        val = (result[0],)
        mycursor.execute(sql, val)
        mydb.commit()

    sleep(6)
