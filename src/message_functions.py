import sys
from datetime import datetime
import tipper_functions
import text
from tipper_functions import (
    parse_text,
    add_history_record,
    TipError,
    update_history_notes,
    parse_raw_amount,
    send_pm,
    activate,
)
from tipper_rpc import (
    check_balance,
    open_or_receive,
    nano_to_raw,
    validate_address,
    send,
)
from text import WELCOME_CREATE, HELP, WELCOME_TIP, COMMENT_FOOTER, NEW_TIP
from shared import (
    MYCURSOR,
    MYDB,
    TIP_BOT_USERNAME,
    PROGRAM_MINIMUM,
    REDDIT,
    EXCLUDED_REDDITORS,
    LOGGER,
    TIPBOT_OWNER,
)


def handle_message(message):
    # activate the account
    activate(message.author)
    response = "not activated"
    parsed_text = parse_text(str(message.body))

    # standard things
    if (parsed_text[0].lower() == "help") or (parsed_text[0].lower() == "!help"):
        LOGGER.info("Helping")
        subject = "Nano Tipper - Help"
        response = handle_help(message)
    elif (parsed_text[0].lower() == "balance") or (parsed_text[0].lower() == "address"):
        LOGGER.info("balance")
        subject = "Nano Tipper - Account Balance"
        response = handle_balance(message)
    elif parsed_text[0].lower() == "minimum":
        LOGGER.info("Setting Minimum")
        subject = "Nano Tipper - Tip Minimum"
        response = handle_minimum(message)
    elif parsed_text[0].lower() == "percentage" or parsed_text[0].lower() == "percent":
        LOGGER.info("Setting Percentage")
        subject = "Nano Tipper - Returned Tip Percentage for Donation"
        response = handle_percentage(message)
    elif (parsed_text[0].lower() == "create") or parsed_text[0].lower() == "register":
        LOGGER.info("Creating")
        subject = "Nano Tipper - Create"
        response = handle_create(message)
    elif (parsed_text[0].lower() == "send") or (parsed_text[0].lower() == "withdraw"):
        subject = "Nano Tipper - Send"
        LOGGER.info("send via PM")
        response = handle_send(message)
        response = text.make_response_text(message, response)
    elif parsed_text[0].lower() == "history":
        LOGGER.info("history")
        subject = "Nano Tipper - History"
        response = handle_history(message)
    elif parsed_text[0].lower() == "silence":
        LOGGER.info("silencing")
        subject = "Nano Tipper - Silence"
        response = handle_silence(message)
    elif parsed_text[0].lower() == "subreddit":
        LOGGER.info("subredditing")
        subject = "Nano Tipper - Subreddit"
        response = handle_subreddit(message)

    # nanocenter donation commands
    elif parsed_text[0].lower() in ("project", "projects"):
        if (
            (str(message.author) == TIPBOT_OWNER)
            or (str(message.author).lower() == "rockmsockmjesus")
        ) and len(parsed_text) > 2:
            sql = "INSERT INTO projects (project, address) VALUES(%s, %s) ON DUPLICATE KEY UPDATE address=%s"
            val = (parsed_text[1], parsed_text[2], parsed_text[2])
            MYCURSOR.execute(sql, val)
            MYDB.commit()
        add_history_record(
            username=str(message.author),
            action="project",
            comment_text=str(message.body)[:255],
            comment_or_message="message",
            comment_id=message.name,
        )

        response = "Current NanoCenter Donation Projects: \n\n"
        subject = "Nanocenter Projects"
        sql = "SELECT project, address FROM projects"
        MYCURSOR.execute(sql)
        results = MYCURSOR.fetchall()
        for result in results:
            response += "%s %s  \n" % (result[0], result[1])
    elif parsed_text[0].lower() == "delete_project":
        if (
            (str(message.author) == TIPBOT_OWNER)
            or (str(message.author).lower() == "rockmsockmjesus")
        ) and len(parsed_text) > 1:
            sql = "DELETE FROM projects WHERE project=%s"
            val = (parsed_text[1],)
            MYCURSOR.execute(sql, val)
            MYDB.commit()
        response = "Current NanoCenter Donation Projects: \n\n"
        subject = "Nanocenter Projects"
        sql = "SELECT project, address FROM projects"
        MYCURSOR.execute(sql)
        results = MYCURSOR.fetchall()
        for result in results:
            response += "%s %s  \n" % (result[0], result[1])
    # a few administrative tasks
    elif parsed_text[0].lower() in ["restart", "stop", "disable", "deactivate"]:
        if str(message.author).lower() in [
            TIPBOT_OWNER,
            "rockmsockmjesus",
        ]:  # "joohansson"]:
            add_history_record(
                username=str(message.author),
                action="restart",
                comment_text=str(message.body)[:255],
                comment_or_message="message",
                comment_id=message.name,
            )
            sys.exit()
    elif parsed_text[0].lower() == "test_welcome_tipped":
        subject = "Nano Tipper - Welcome By Tip"
        response = WELCOME_TIP % (
            0.01,
            "xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij",
            "xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij",
        )
    elif parsed_text[0].lower() == "test_welcome_create":
        subject = "Nano Tipper - Create"
        response = WELCOME_CREATE % (
            "xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij",
            "xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij",
        )

    else:
        add_history_record(
            username=str(message.author),
            comment_text=str(message.body)[:255],
            comment_or_message="message",
            comment_id=message.name,
        )
        return None
    message_recipient = str(message.author)
    message_text = response + COMMENT_FOOTER
    sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
    val = (message_recipient, subject, message_text)
    MYCURSOR.execute(sql, val)
    MYDB.commit()


def handle_percentage(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    # user may select a minimum tip amount to avoid spamming. Tipbot minimum is 0.001
    username = str(message.author)
    # find any accounts associated with the redditor
    parsed_text = parse_text(str(message.body))

    # there should be at least 2 words, a minimum and an amount.
    if len(parsed_text) < 2:
        response = "I couldn't parse your command. I was expecting 'percentage <amount>'. Be sure to check your spacing."
        return response
    # check that the minimum is a number

    if parsed_text[1].lower() == "nan" or ("inf" in parsed_text[1].lower()):
        response = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."
        return response
    try:
        amount = float(parsed_text[1])
    except:
        response = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."
        return response

    # check that it's greater than 0.01
    if round(amount, 2) < 0:
        response = "Did not update. Your percentage cannot be negative."
        return response

    if round(amount, 2) > 100:
        response = "Did not update. Your percentage must be 100 or lower."
        return response

    # check if the user is in the database
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username,)
    MYCURSOR.execute(sql, val)
    result = MYCURSOR.fetchall()
    if len(result) > 0:
        # open_or_receive(result[0][0], result[0][1])
        # balance = check_balance(result[0][0])
        add_history_record(
            username=username,
            action="percentage",
            amount=round(amount, 2),
            address=result[0][0],
            comment_or_message="message",
            comment_id=message.name,
            reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
            comment_text=str(message.body)[:255],
        )
        sql = "UPDATE accounts SET percentage = %s WHERE username = %s"
        val = (round(amount, 2), username)
        MYCURSOR.execute(sql, val)
        MYDB.commit()
        response = "Updating donation percentage to %s" % round(amount, 2)
        return response
    else:
        add_history_record(
            username=username,
            action="percentage",
            reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
            amount=round(amount, 2),
            comment_id=message.name,
            comment_text=str(message.body)[:255],
        )
        response = (
            "You do not currently have an account open. To create one, "
            "respond with the text 'create' in the message body."
        )
        return response


def handle_balance(message):
    username = str(message.author)
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message="message",
        reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
        action="balance",
        comment_id=message.name,
        comment_text=str(message.body)[:255],
    )
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username,)
    MYCURSOR.execute(sql, val)
    result = MYCURSOR.fetchall()
    if len(result) > 0:
        results = check_balance(result[0][0])

        response = (
            "At address %s:\n\nAvailable: %s Nano\n\nUnpocketed: %s Nano\n\nNano "
            "will be pocketed automatically unless the transaction is below "
            "0.0001 Nano."
            "\n\nhttps://nanocrawler.cc/explorer/account/%s"
            % (result[0][0], results[0] / 10 ** 30, results[1] / 10 ** 30, result[0][0])
        )

        return response
    return "You do not have an open account yet"


def handle_create(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message="message",
        reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
        action="create",
        comment_id=message.name,
        comment_text=str(message.body)[:255],
    )

    username = str(message.author)
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username,)
    MYCURSOR.execute(sql, val)
    result = MYCURSOR.fetchall()
    if len(result) is 0:
        address = tipper_functions.add_new_account(username)
        response = WELCOME_CREATE % (address, address)
        message_recipient = TIP_BOT_USERNAME
        subject = "send"
        message_text = "send 0.001 %s" % username
        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (message_recipient, subject, message_text)
        MYCURSOR.execute(sql, val)
        MYDB.commit()

        # reddit.redditor(message_recipient).message(subject, message_text)

    else:
        response = (
            "It looks like you already have an account. In any case it is now "
            "**active**. Your Nano address is %s."
            "\n\nhttps://nanocrawler.cc/explorer/account/%s"
            % (result[0][0], result[0][0])
        )
    return response


def handle_help(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        action="help",
        comment_or_message="message",
        comment_id=message.name,
        reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
    )
    response = HELP
    return response


def handle_history(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    username = str(message.author)
    parsed_text = parse_text(str(message.body))
    num_records = 10
    # if there are more than 2 words, one of the words is a number for the number of records
    if len(parsed_text) >= 2:
        if parsed_text[1].lower() == "nan" or ("inf" in parsed_text[1].lower()):
            response = (
                "'%s' didn't look like a number to me. If it is blank, "
                "there might be extra spaces in the command."
            )
            return response
        try:
            num_records = int(parsed_text[1])
        except:
            response = (
                "'%s' didn't look like a number to me. If it is blank, "
                "there might be extra spaces in the command."
            )
            return response

    # check that it's greater than 50
    if num_records > 50:
        num_records = 50

    # check if the user is in the database
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username,)
    MYCURSOR.execute(sql, val)
    result = MYCURSOR.fetchall()
    if len(result) > 0:
        # open_or_receive(result[0][0], result[0][1])
        # balance = check_balance(result[0][0])
        add_history_record(
            username=username,
            action="history",
            amount=num_records,
            address=result[0][0],
            comment_or_message="message",
            comment_id=message.name,
            reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
            comment_text=str(message.body)[:255],
        )
        response = "Here are your last %s historical records:\n\n" % num_records
        sql = (
            "SELECT reddit_time, action, amount, comment_id, notes, recipient_"
            "username, recipient_address FROM history WHERE username=%s ORDER BY "
            "id DESC limit %s"
        )
        val = (username, num_records)
        MYCURSOR.execute(sql, val)
        results = MYCURSOR.fetchall()
        for result in results:
            try:
                amount = result[2]
                if (result[1] == "send") and amount:
                    amount = int(result[2]) / 10 ** 30
                    if (
                        result[4] == "sent to registered redditor"
                        or result[4] == "new user created"
                    ):
                        response += (
                            "%s: %s | %s Nano to %s | reddit object: %s | %s\n\n"
                            % (
                                result[0],
                                result[1],
                                amount,
                                result[5],
                                result[3],
                                result[4],
                            )
                        )
                    elif (
                        result[4] == "sent to registered address"
                        or result[4] == "sent to unregistered address"
                    ):
                        response += (
                            "%s: %s | %s Nano to %s | reddit object: %s | %s\n\n"
                            % (
                                result[0],
                                result[1],
                                amount,
                                result[6],
                                result[3],
                                result[4],
                            )
                        )
                elif result[1] == "send":
                    response += "%s: %s | reddit object: %s | %s\n\n" % (
                        result[0],
                        result[1],
                        result[3],
                        result[4],
                    )
                elif (result[1] == "minimum") and amount:
                    amount = int(result[2]) / 10 ** 30
                    response += "%s: %s | %s | %s | %s\n\n" % (
                        result[0],
                        result[1],
                        amount,
                        result[3],
                        result[4],
                    )
                else:
                    response += "%s: %s | %s | %s | %s\n\n" % (
                        result[0],
                        result[1],
                        amount,
                        result[3],
                        result[4],
                    )
            except:
                response += (
                    "Unparsed Record: Nothing is wrong, I just didn't "
                    "parse this record properly.\n\n"
                )

        return response
    else:
        add_history_record(
            username=username,
            action="history",
            reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
            amount=num_records,
            comment_id=message.name,
            comment_text=str(message.body)[:255],
        )
        response = (
            "You do not currently have an account open. To create one, "
            "respond with the text 'create' in the message body."
        )
        return response


def handle_minimum(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    # user may select a minimum tip amount to avoid spamming. Tipbot minimum is 0.001
    username = str(message.author)
    # find any accounts associated with the redditor
    parsed_text = parse_text(str(message.body))

    # there should be at least 2 words, a minimum and an amount.
    if len(parsed_text) < 2:
        response = (
            "I couldn't parse your command. I was expecting 'minimum "
            "<amount>'. Be sure to check your spacing."
        )
        return response
    # check that the minimum is a number

    if parsed_text[1].lower() == "nan" or ("inf" in parsed_text[1].lower()):
        response = (
            "'%s' didn't look like a number to me. If it is blank, "
            "there might be extra spaces in the command."
        )
        return response
    try:
        amount = float(parsed_text[1])
    except:
        response = (
            "'%s' didn't look like a number to me. If it is blank, "
            "there might be extra spaces in the command."
        )
        return response

    # check that it's greater than 0.01
    if nano_to_raw(amount) < nano_to_raw(PROGRAM_MINIMUM):
        response = (
            "Did not update. The amount you specified is below the program minimum "
            "of %s Nano." % PROGRAM_MINIMUM
        )
        return response

    # check if the user is in the database
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username,)
    MYCURSOR.execute(sql, val)
    result = MYCURSOR.fetchall()
    if len(result) > 0:
        # open_or_receive(result[0][0], result[0][1])
        # balance = check_balance(result[0][0])
        add_history_record(
            username=username,
            action="minimum",
            amount=nano_to_raw(amount),
            address=result[0][0],
            comment_or_message="message",
            comment_id=message.name,
            reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
            comment_text=str(message.body)[:255],
        )
        sql = "UPDATE accounts SET minimum = %s WHERE username = %s"
        val = (str(nano_to_raw(amount)), username)
        MYCURSOR.execute(sql, val)
        MYDB.commit()
        response = "Updating tip minimum to %s" % amount
        return response
    else:
        add_history_record(
            username=username,
            action="minimum",
            reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
            amount=nano_to_raw(amount),
            comment_id=message.name,
            comment_text=str(message.body)[:255],
        )
        response = (
            "You do not currently have an account open. To create one, "
            "respond with the text 'create' in the message body."
        )
        return response


def handle_receive(message):
    """

    :param message:
    :return:
    """
    message_time = datetime.utcfromtimestamp(message.created_utc)
    username = str(message.author)
    # find any accounts associated with the redditor
    sql = "SELECT address, private_key FROM accounts WHERE username=%s"
    val = (username,)
    MYCURSOR.execute(sql, val)
    result = MYCURSOR.fetchall()
    if len(result) > 0:
        address = result[0][0]
        open_or_receive(address, result[0][1])
        balance = check_balance(address)
        add_history_record(
            username=username,
            action="receive",
            reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
            address=address,
            comment_id=message.name,
            comment_or_message="message",
        )
        response = (
            "At address %s, you currently have %s Nano available, and %s Nano "
            "unpocketed. If you have any unpocketed, create a new "
            "message containing the word "
            "'receive'\n\nhttps://nanocrawler.cc/explorer/account/%s"
            % (address, balance[0] / 10 ** 30, balance[1] / 10 ** 30, address)
        )
        return response
    else:
        add_history_record(
            username=username,
            action="receive",
            reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
            comment_id=message.name,
            comment_or_message="message",
        )
        response = (
            "You do not currently have an account open. To create one, "
            "respond with the text 'create' in the message body."
        )
        return response


def handle_silence(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    username = str(message.author)
    add_history_record(
        username=str(message.author),
        action="silence",
        comment_or_message="message",
        comment_id=message.name,
        reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
    )

    parsed_text = parse_text(str(message.body))

    if len(parsed_text) < 2:
        response = (
            "I couldn't parse your command. I was expecting 'silence "
            "<yes/no>'. Be sure to check your spacing."
        )
        return response

    if parsed_text[1] == "yes":
        sql = "UPDATE accounts SET silence = TRUE WHERE username = %s "
        val = (username,)
        MYCURSOR.execute(sql, val)
        response = (
            "Silence set to 'yes'. You will no longer receive tip "
            "notifications or be tagged by the bot."
        )
    elif parsed_text[1] == "no":
        sql = "UPDATE accounts SET silence = FALSE WHERE username = %s"
        val = (username,)
        MYCURSOR.execute(sql, val)
        response = (
            "Silence set to 'no'. You will receive tip notifications and be "
            "tagged by the bot in replies."
        )
    else:
        response = (
            "I did not see 'no' or 'yes' after 'silence'. If you did type "
            "that, check your spacing."
        )
    MYDB.commit()

    return response


def handle_subreddit(message):

    parsed_text = parse_text(str(message.body))
    # check if there are at least 3 items (command, sub, action, option)
    if len(parsed_text) < 3:
        return "Your command seems to be missing something. Make sure it follow the format `subreddit <subreddit> <command> <option>.`"
    # check if the user is a moderator of the subreddit
    if message.author not in REDDIT.subreddit(parsed_text[1]).moderator():
        return "You are not a moderator of /r/%s." % parsed_text[1]

    if parsed_text[2] == "minimum":
        return "Subreddit-specific minimums aren't enabled yet. Check back soon!"

    if parsed_text[2] in ("disable", "deactivate"):
        # disable the bot
        try:
            sql = "DELETE FROM subreddits WHERE subreddit=%s"
            val = (parsed_text[1],)
            MYCURSOR.execute(sql, val)
            MYDB.commit()
        except:
            pass
        return (
            "Within 5 minutes, tipping will be deactivated in your subreddit %s."
            % parsed_text[1]
        )

    if parsed_text[2] in ("enable", "activate"):
        # if it's at least 4 words, set the status to that one
        if (len(parsed_text) > 3) and (parsed_text[3] in ["full", "minimal", "silent"]):
            status = parsed_text[3]
        else:
            status = "full"
        # sql to change subreddit to that status
        try:
            sql = "INSERT INTO subreddits (subreddit, reply_to_comments, footer, status) VALUES (%s, %s, %s, %s)"
            val = (parsed_text[1], True, None, status)
            MYCURSOR.execute(sql, val)
            MYDB.commit()
        except:
            sql = "UPDATE subreddits SET status = %s WHERE subreddit = %s"
            val = (status, parsed_text[1])
            MYCURSOR.execute(sql, val)
            MYDB.commit()
        return (
            "Within 5 minutes, the tipbot response in your Subreddit will be set to %s."
            % status
        )

    # only 4 word commands after this point
    if len(parsed_text) < 4:
        return "There was something wrong with your activate or minimum command."


def handle_send(message):
    """
    Extracts send command information from a PM command
    :param message:
    :return:
    """
    parsed_text = parse_text(str(message.body))
    username = str(message.author)
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    entry_id = add_history_record(
        username=username,
        action="send",
        comment_or_message="message",
        comment_id=message.name,
        reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
        comment_text=str(message.body)[:255],
    )
    response = {"username": username}

    # check that there are enough fields (i.e. a username)
    if len(parsed_text) <= 2:
        update_history_notes(entry_id, "no recipient or amount specified")
        response["status"] = 110
        return response

    # check that it wasn't a mistyped currency code or something
    if parsed_text[2] in EXCLUDED_REDDITORS:
        response["status"] = 140
        return response

    # pull sender account info
    sender_info = tipper_functions.account_info(response["username"])
    if not sender_info:
        update_history_notes(entry_id, "user does not exist")
        response["status"] = 100
        return response

    # parse the amount
    try:
        response["amount"] = parse_raw_amount(parsed_text, response["username"])
    except TipError as err:
        response["status"] = 120
        response["amount"] = parsed_text[1]
        update_history_notes(entry_id, err.sql_text)
        return response

    # check if it's above the program minimum
    if response["amount"] < nano_to_raw(PROGRAM_MINIMUM):
        update_history_notes(entry_id, "amount below program limit")
        response["status"] = 130
        return response

    # check the user's balance
    if response["amount"] > sender_info["balance"]:
        update_history_notes(entry_id, "insufficient funds")
        response["status"] = 160
        return response

    recipient_text = parsed_text[2]

    # catch invalid redditor AND address
    try:
        recipient_info = parse_recipient_username(recipient_text)
    except TipError as err:
        update_history_notes(entry_id, err.sql_text)
        response["recipient"] = recipient_text
        response["status"] = 170
        return response

    # if we have a username, pull their info
    if "username" in recipient_info.keys():
        response["recipient"] = recipient_info["username"]
        recipient_name = recipient_info["username"]
        recipient_info = tipper_functions.account_info(recipient_name)
        response["status"] = 10
        if recipient_info is None:
            recipient_info = tipper_functions.add_new_account(response["recipient"])
            response["status"] = 20
    # check if it's an address
    else:
        # otherwise, just use the address. Everything is None except address
        recipient_info["minimum"] = 0
        response["recipient"] = recipient_info["address"]
        response["status"] = 30

    # check the send amount is above the user minimum, if a username is provided
    # if it was just an address, this would be -1
    if response["amount"] < recipient_info["minimum"]:
        update_history_notes(entry_id, "below user minimum")
        response["status"] = 180
        response["minimum"] = recipient_info["minimum"]
        return response

    response["hash"] = send(
        sender_info["address"],
        sender_info["private_key"],
        response["amount"],
        recipient_info["address"],
    )["hash"]
    # if it was an address, just send to the address
    if "username" not in recipient_info.keys():
        sql = (
            "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, "
            "recipient_address = %s, amount = %s, return_status = %s WHERE id = %s"
        )
        val = (
            "send to address",
            sender_info["address"],
            sender_info["username"],
            None,
            recipient_info["address"],
            str(response["amount"]),
            "cleared",
            entry_id,
        )
        tipper_functions.exec_sql(sql, val)
        LOGGER.info(
            f"Sending Nano: {sender_info['address']} {sender_info['private_key']} {response['amount']} {recipient_info['address']}"
        )
        return response

    # Update the sql and send the PMs
    sql = (
        "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, "
        "recipient_address = %s, amount = %s, return_status = %s WHERE id = %s"
    )
    val = (
        "sent to user",
        sender_info["address"],
        sender_info["username"],
        recipient_info["username"],
        recipient_info["address"],
        str(response["amount"]),
        "cleared",
        entry_id,
    )
    tipper_functions.exec_sql(sql, val)
    LOGGER.info(
        f"Sending Nano: {sender_info['address']} {sender_info['private_key']} {response['amount']} {recipient_info['address']} {recipient_info['username']}"
    )

    if response["status"] == 20:
        subject = "Congrats on receiving your first Nano Tip!"
        message_text = (
            WELCOME_TIP
            % (
                response["amount"] / 10 ** 30,
                recipient_info["address"],
                recipient_info["address"],
            )
            + COMMENT_FOOTER
        )
        send_pm(recipient_info["username"], subject, message_text)
        return response
    else:
        if not recipient_info["silence"]:
            receiving_new_balance = check_balance(recipient_info["address"])
            subject = "You just received a new Nano tip!"
            message_text = (
                NEW_TIP
                % (
                    response["amount"] / 10 ** 30,
                    recipient_info["address"],
                    receiving_new_balance[0] / 10 ** 30,
                    (
                        receiving_new_balance[1] / 10 ** 30
                        + response["amount"] / 10 ** 30
                    ),
                    response["hash"],
                )
                + COMMENT_FOOTER
            )
            send_pm(recipient_info["username"], subject, message_text)
        return response


def parse_recipient_username(recipient_text):
    """
    Determines if a specified recipient is a nano address or a redditor
    :param recipient_text:
    :return: either {address: valid_address} or {username: user}
    """
    # remove the /u/ or u/
    if recipient_text[:3].lower() == "/u/":
        recipient_text = recipient_text[3:]
    elif recipient_text[:2].lower() == "u/":
        recipient_text = recipient_text[2:]

    if (recipient_text[:5].lower() == "nano_") or (
        recipient_text[:4].lower() == "xrb_"
    ):
        # check valid address
        success = validate_address(recipient_text)
        if success["valid"] == "1":
            return {"address": recipient_text}
        # if not, check if it is a redditor disguised as an address (e.g.
        # nano_is_awesome, nano_tipper_z)
        else:
            try:
                _ = getattr(REDDIT.redditor(recipient_text), "is_suspended", False)
                return {"username": recipient_text}
            except:
                raise TipError(
                    "invalid address or address-like redditor does not exist",
                    "%s is neither a valid address nor a redditor" % recipient_text,
                )
    else:
        # a username was specified
        try:
            _ = getattr(REDDIT.redditor(recipient_text), "is_suspended", False)
            return {"username": recipient_text}
        except:
            raise TipError(
                "redditor does not exist",
                "Could not find redditor %s. Make sure you aren't writing or "
                "copy/pasting markdown." % recipient_text,
            )
