from time import sleep
from shared import MYDB, MYCURSOR, REDDIT, LOGGER

while True:
    sql = "SELECT * FROM messages"
    MYCURSOR.execute(sql)
    results = MYCURSOR.fetchall()
    MYDB.commit()

    for result in results:
        LOGGER.info(
            "%s %s %s %s" % (result[1], result[2], result[4], repr(result[3])[:50])
        )

        try:
            # find the message to reply to it.
            if result[4] is not None:
                msg = REDDIT.inbox.message(result[4].replace("t4_", ""))
                msg.reply(str(result[3]))
            # if it was a comment, create a new message
            else:
                REDDIT.redditor(str(result[1])).message(str(result[2]), str(result[3]))
        except:
            pass
        sql = "DELETE FROM messages WHERE id = %s"
        val = (result[0],)
        MYCURSOR.execute(sql, val)
        MYDB.commit()

    sleep(6)
