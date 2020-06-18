from datetime import datetime
import tipper_functions
from tipper_functions import (
    parse_text,
    add_history_record,
    add_new_account,
    TipError,
    account_info,
    update_history_notes,
    parse_raw_amount,
    validate_address,
    send,
)
from tipper_rpc import check_balance, open_or_receive, nano_to_raw
from shared import (
    MYCURSOR,
    MYDB,
    WELCOME_CREATE,
    TIP_BOT_USERNAME,
    HELP,
    PROGRAM_MINIMUM,
    REDDIT,
    EXCLUDED_REDDITORS,
    LOGGER,
    WELCOME_TIP,
    COMMENT_FOOTER,
    NEW_TIP,
)


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
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
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
            "At address %s:\n\nAvailable: %s Nano\n\nUnpocketed: %s Nano\n\nNano will be pocketed automatically unless the transaction is below 0.0001 Nano."
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
        address = add_new_account(username)
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
            "It looks like you already have an account. In any case it is now **active**. Your Nano address is %s."
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
            response = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."
            return response
        try:
            num_records = int(parsed_text[1])
        except:
            response = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."
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
        sql = "SELECT reddit_time, action, amount, comment_id, notes, recipient_username, recipient_address FROM history WHERE username=%s ORDER BY id DESC limit %s"
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
                response += "Unparsed Record: Nothing is wrong, I just didn't parse this record properly.\n\n"

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
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
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
        response = "I couldn't parse your command. I was expecting 'minimum <amount>'. Be sure to check your spacing."
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
    if nano_to_raw(amount) < nano_to_raw(PROGRAM_MINIMUM):
        response = (
            "Did not update. The amount you specified is below the program minimum of %s Nano."
            % PROGRAM_MINIMUM
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
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
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
            "At address %s, you currently have %s Nano available, and %s Nano unpocketed. If you have any unpocketed, create a new "
            "message containing the word 'receive'\n\nhttps://nanocrawler.cc/explorer/account/%s"
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
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
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
        response = "I couldn't parse your command. I was expecting 'silence <yes/no>'. Be sure to check your spacing."
        return response

    if parsed_text[1] == "yes":
        sql = "UPDATE accounts SET silence = TRUE WHERE username = %s "
        val = (username,)
        MYCURSOR.execute(sql, val)
        response = "Silence set to 'yes'. You will no longer receive tip notifications or be tagged by the bot."
    elif parsed_text[1] == "no":
        sql = "UPDATE accounts SET silence = FALSE WHERE username = %s"
        val = (username,)
        MYCURSOR.execute(sql, val)
        response = "Silence set to 'no'. You will receive tip notifications and be tagged by the bot in replies."
    else:
        response = "I did not see 'no' or 'yes' after 'silence'. If you did type that, check your spacing."
    MYDB.commit()

    return response


def handle_subreddit(message):

    parsed_text = parse_text(str(message.body))
    # check if there are at least 3 items (command, sub, action, option)
    if len(parsed_text) < 3:
        return "Your command seems to be missing something. Make sure it follow the format `subreddit <subreddit> <command> <option>.`"
    # check if the user is a moderator of the subreddit
    if message.author not in REDDIT.subreddit(parsed_text[1]).moderator():
        return "You are not a moderator of the subreddit."

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
            "Tipping via !ntip has been deactivated in your subreddit %s"
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
        return "Set the tipbot response in your Subreddit to %s" % status

    # only 4 word commands after this point
    if len(parsed_text) < 4:
        return "There was something wrong with your activate or minimum command."


def handle_send(message):
    """
    Extracts send command information from a PM command
    :param message:
    :return:
    """
    new_account = True
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
    # check that there are enough fields (i.e. a username)
    if len(parsed_text) == 2:
        update_history_notes(entry_id, "no recipient specified")
        response = "You must specify an amount and a user."
        return response

    # pull sender account info
    try:
        sender = tipper_functions.account_info(username=username)
    except TipError as err:
        update_history_notes(entry_id, err.sql_text)
        return err.response

    # parse the amount
    try:
        amount = parse_raw_amount(parsed_text)
    except TipError as err:
        update_history_notes(entry_id, err.sql_text)
        return err.response

    # check if it's above the program minimum
    if amount < nano_to_raw(PROGRAM_MINIMUM):
        update_history_notes(entry_id, "amount below program limit")
        response = "Program minimum is %s Nano." % PROGRAM_MINIMUM
        return response

    # check the user's balance
    if amount > sender["balance"]:
        update_history_notes(entry_id, "insufficient funds")
        response = "You have insufficient funds. Please check your balance."
        return response

    recipient_text = parsed_text[2]

    try:
        recipient = parse_recipient_username(recipient_text)
    except TipError as err:
        update_history_notes(entry_id, err.sql_text)
        return err.response

    # if we have a username, pull their info
    try:
        recipient = account_info(recipient["username"])
    except TipError:
        # user does not exist, create
        recipient = new_account(recipient["username"])
    except KeyError:
        # otherwise, just use the address. Everything is None except address
        recipient = account_info(recipient["address"])

    # check that it wasn't a mistyped currency code or something
    if recipient["username"] in EXCLUDED_REDDITORS:
        response = (
            "Sorry, the redditor '%s' is in the list of excluded addresses. More than likely you didn't intend to send to that user."
            % (recipient["username"])
        )
        return response

    # check the send amount is above the user minimum, if a username is provided
    # if it was just an address, this would be -1
    if amount >= recipient["minimum"]:
        update_history_notes(entry_id, "below user minimum")
        response = (
            "Sorry, the user has set a tip minimum of %s. "
            "Your tip of %s is below this amount."
            % (recipient["minimum"] / 10 ** 30, amount / 10 ** 30)
        )
        return response

    sent = send(sender["address"], sender["private_key"], amount, recipient["address"])

    if "username" not in recipient.keys():
        notes = "sent to address"
        sql = (
            "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, "
            "recipient_address = %s, amount = %s WHERE id = %s"
        )
        val = (
            notes,
            sender["address"],
            username,
            None,
            recipient["address"],
            str(amount),
            entry_id,
        )
        MYCURSOR.execute(sql, val)
        MYDB.commit()
        LOGGER.info(
            f"Sending Nano: {sender['address']} {sender['private_key']} {amount} {recipient['address']} {recipient['username']}"
        )
        return (
            "Sent ```%.4g Nano``` to [%s](https://nanocrawler.cc/explorer/account/%s) -- "
            "[Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)"
            % (
                amount / 10 ** 30,
                recipient["address"],
                recipient["address"],
                sent["hash"],
            )
        )

    #
    sql = (
        "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, "
        "recipient_address = %s, amount = %s WHERE id = %s"
    )
    val = (
        "sent to user",
        sender["address"],
        username,
        recipient["username"],
        recipient["address"],
        str(amount),
        entry_id,
    )
    MYCURSOR.execute(sql, val)
    MYDB.commit()
    LOGGER.info(
        f"Sending Nano: {sender['address']} {sender['private_key']} {amount} {recipient['address']} {recipient['username']}"
    )

    if new_account:
        subject = "Congrats on receiving your first Nano Tip!"
        message_text = (
            WELCOME_TIP
            % (amount / 10 ** 30, recipient["address"], recipient["address"])
            + COMMENT_FOOTER
        )

        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (recipient["username"], subject, message_text)
        MYCURSOR.execute(sql, val)
        MYDB.commit()
        return (
            "Creating a new account for /u/%s and "
            "sending ```%.4g Nano```. [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)"
            % (recipient["username"], amount / 10 ** 30, sent["hash"])
        )
    elif recipient["silence"]:
        return (
            "Sent ```%.4g Nano``` to /u/%s -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)"
            % (amount / 10 ** 30, recipient["username"], sent["hash"])
        )
    else:
        receiving_new_balance = check_balance(recipient["address"])
        subject = "You just received a new Nano tip!"
        message_text = (
            NEW_TIP
            % (
                amount / 10 ** 30,
                recipient["address"],
                receiving_new_balance[0] / 10 ** 30,
                (receiving_new_balance[1] / 10 ** 30 + amount / 10 ** 30),
                sent["hash"],
            )
            + COMMENT_FOOTER
        )

        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (recipient["username"], subject, message_text)
        MYCURSOR.execute(sql, val)
        MYDB.commit()
        return (
            "Sent ```%.4g Nano``` to /u/%s -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)"
            % (amount / 10 ** 30, recipient["username"], sent["hash"])
        )


def parse_recipient_username(recipient_text):
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
                recipient = {"username": recipient_text}
            except:
                raise TipError(
                    "invalid address or address-like redditor does not exist",
                    "%s is neither a valid address nor a redditor" % recipient,
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
