from time import sleep
from shared import REDDIT, LOGGER, Message

LOGGER.info("Starting messenger")
while True:
    results = Message.select()
    for result in results:
        LOGGER.info("%s %s %s" % (result.username, result.subject, repr(result.message)[:50]))

        try:
            REDDIT.redditor(str(result.username)).message(str(result.subject), str(result.message))
        except:
            pass
        Message.delete().where(Message.id == result.id).execute()

    sleep(6)
