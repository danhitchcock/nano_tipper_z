import sys
import time
import datetime
from time import sleep
from tipper_rpc import get_pendings, open_or_receive_block
from shared import (
    TIPBOT_OWNER,
    TIP_COMMANDS,
    TIP_BOT_ON,
    LOGGER,
    MYCURSOR,
    MYDB,
    REDDIT,
    COMMENT_FOOTER,
    WELCOME_CREATE,
    WELCOME_TIP,
    PROGRAM_MINIMUM,
    HELP,
    DONATE_COMMANDS,
    TIP_BOT_USERNAME,
)
from message_functions import (
    handle_balance,
    handle_create,
    handle_help,
    handle_history,
    handle_minimum,
    handle_percentage,
    handle_send,
    handle_silence,
    handle_subreddit,
    add_history_record,
)
from tipper_functions import (
    parse_text,
    handle_send_nano,
    nano_to_raw,
    allowed_request,
    send,
    activate,
)

CYCLE_TIME = 6
# initiate the bot and all friendly subreddits
def get_subreddits():
    MYCURSOR.execute("SELECT subreddit FROM subreddits")
    results = MYCURSOR.fetchall()
    LOGGER.info(f"Initializing in the following subreddits: {results}")
    MYDB.commit()
    if len(results) == 0:
        return None
    subreddits = ""
    for result in results:
        subreddits += "%s+" % result[0]
    subreddits = subreddits[:-1]
    return REDDIT.subreddit(subreddits)


SUBREDDITS = get_subreddits()


# a few globals.
toggle_receive = True


def stream_comments_messages():
    """
    # generator to stream comments and messages to the main loop at the bottom, and contains the auto_receive functionality.
    # Maybe this wasn't necessary, but I never get to use generators.
    # To check for new messages and comments, the function scans the subreddits and inbox every 6 seconds and builds a
    # set of current message. I compare the old set with the new set.
    :return:
    """
    previous_time = time.time()
    previous_comments = {comment for comment in SUBREDDITS.comments()}
    previous_messages = {message for message in REDDIT.inbox.all(limit=25)}

    while True:
        try:
            sleep(CYCLE_TIME - (time.time() - previous_time))
        except ValueError:
            pass
        previous_time = time.time()

        # check for new comments
        updated_comments = {comment for comment in SUBREDDITS.comments()}
        new_comments = updated_comments - previous_comments
        previous_comments = updated_comments

        # check for new messages
        updated_messages = {message for message in REDDIT.inbox.all(limit=25)}
        new_messages = updated_messages - previous_messages
        previous_messages = updated_messages

        total_new = new_comments.union(new_messages)
        if len(total_new) >= 1:
            for item in total_new:
                yield item
        else:
            yield None


# handles tip commands on subreddits
def handle_comment(message, parsed_text=None):
    """
    Prepares a reddit comment starting with !nano_tip to send nano if everything goes well
    :param message:
    :param parsed_text
    :return:
    """
    # Pull the relevant text for the actual command
    if parsed_text is None:
        parsed_text = parse_text(str(message.body))
    # check if it's a donate command at the end
    if parsed_text[-3] in DONATE_COMMANDS:
        parsed_text = parsed_text[-3:]
    # check if it's a send command at the end
    if parsed_text[-2] in TIP_COMMANDS:
        parsed_text = parsed_text[-2:]

    # attempt to parse the message, send the Nano, and record responses
    # response is a 6-member list with some info
    # response[0] - message to the tip sender
    # response[1] - a status code
    # response[2] - Tip amount in 'Nano'
    # response[3] - reddit username
    # response[4] - reddit address
    # response[5] - transaction hash
    # If the recipient is new, it will automatically send a welcome greeting.
    response = handle_send_nano(message, parsed_text, "comment")

    # apply the subreddit rules to our response message
    # potential statuses:
    #   friendly
    #   hostile
    #   minimal
    # if it is a friendly subreddit, just reply with the response + comment_footer
    # if it is not friendly, we need to notify the sender as well as the recipient if they have not elected silence
    # handle top level comment
    sql = "SELECT status FROM subreddits WHERE subreddit=%s"
    val = (str(message.subreddit).lower(),)
    MYCURSOR.execute(sql, val)
    results = MYCURSOR.fetchall()

    if len(results) == 0:
        subreddit_status = "silent"
    else:
        subreddit_status = results[0][0]
    # if it is a top level reply and the subreddit is friendly
    if (str(message.parent_id)[:3] == "t3_") and (
        subreddit_status in ["friendly", "full"]
    ):
        message.reply(response[0] + COMMENT_FOOTER)
    # otherwise, if the subreddit is friendly (and reply is not top level) or subreddit is minimal
    elif subreddit_status in ["friendly", "minimal", "full"]:
        if response[1] <= 8:
            message.reply(
                "^(Tip not sent. Error code )^[%s](https://github.com/danhitchcock/nano_tipper_z#error-codes) ^- [^(Nano Tipper)](https://github.com/danhitchcock/nano_tipper_z)"
                % response[1]
            )
        elif response[1] == 9:
            message.reply(
                "^[Sent](https://nanocrawler.cc/explorer/block/%s) ^%s ^Nano ^to ^%s ^- [^(Nano Tipper)](https://github.com/danhitchcock/nano_tipper_z)"
                % (response[5], response[2], response[3])
            )
        elif (response[1] == 10) or (response[1] == 13):
            # user didn't request silence or it's a new account, so tag them
            message.reply(
                "^[Sent](https://nanocrawler.cc/explorer/block/%s) ^%s ^Nano ^to ^(/u/%s) ^- [^(Nano Tipper)](https://github.com/danhitchcock/nano_tipper_z)"
                % (response[5], response[2], response[3])
            )
        elif (response[1] == 11) or (response[1] == 12):
            # this actually shouldn't ever happen
            message.reply(
                "^[Sent](https://nanocrawler.cc/explorer/block/%s) ^(%s Nano to %s)"
                % (response[5], response[2], response[4])
            )
        elif response[1] == 14:
            message.reply(
                "^[Sent](https://nanocrawler.cc/explorer/block/%s) ^(%s Nano to NanoCenter Project %s)"
                % (response[5], response[2], response[3])
            )
    elif subreddit_status in ["hostile", "silent"]:
        # it's a hostile place, no posts allowed. Will need to PM users
        if response[1] <= 8:
            message_recipient = str(message.author)
            subject = "Your Nano tip did not go through"
            message_text = response[0] + COMMENT_FOOTER
            sql = (
                "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
            )
            val = (message_recipient, subject, message_text)
            MYCURSOR.execute(sql, val)
            MYDB.commit()
        else:
            # if it was a new account, a PM was already sent to the recipient
            message_recipient = str(message.author)
            subject = "Successful tip!"
            message_text = response[0] + COMMENT_FOOTER
            sql = (
                "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
            )
            val = (message_recipient, subject, message_text)
            MYCURSOR.execute(sql, val)
            MYDB.commit()
            # status code 10 means the recipient has not requested silence, so send a message
            if response[1] == 10:
                message_recipient = response[3]
                subject = "You just received a new Nano tip!"
                message_text = (
                    "Somebody just tipped you ```%s Nano``` at your address %s. "
                    "[Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)\n\n"
                    'To turn off these notifications, reply with "silence yes"'
                    % (response[2], response[4], response[5])
                    + COMMENT_FOOTER
                )

                sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
                val = (message_recipient, subject, message_text)
                MYCURSOR.execute(sql, val)
                MYDB.commit()

    elif subreddit_status == "custom":
        # not sure what to do with this yet.
        pass


# These functions below handle the various messages the bot will receive
def handle_auto_receive(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    username = str(message.author)
    add_history_record(
        username=str(message.author),
        action="auto_receive",
        comment_id=message.name,
        comment_or_message="message",
        reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
    )

    parsed_text = parse_text(str(message.body))

    if len(parsed_text) < 2:
        response = (
            "I couldn't parse your command. I was expecting 'auto_receive <yes/no>'. "
            "Be sure to check your spacing."
        )
        return response

    if parsed_text[1] == "yes":
        sql = "UPDATE accounts SET auto_receive = TRUE WHERE username = %s "
        val = (username,)
        MYCURSOR.execute(sql, val)
        response = "auto_receive set to 'yes'."
    elif parsed_text[1] == "no":
        sql = "UPDATE accounts SET auto_receive = FALSE WHERE username = %s"
        val = (username,)
        MYCURSOR.execute(sql, val)
        response = "auto_receive set to 'no'. Use 'receive' to manually receive unpocketed transactions."
    else:
        response = "I did not see 'no' or 'yes' after 'auto_receive'. If you did type that, check your spacing."
    MYDB.commit()

    return response


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
        global subreddits
        subreddits = get_subreddits()
        LOGGER.info(subreddits)

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
    elif parsed_text[0].lower() == "status":
        # benchmark a few SQL Selects
        if str(message.author) == TIPBOT_OWNER:
            previous_message_check = time.time()
            message_in_database(message)
            previous_message_check = previous_message_check - time.time()
            subject = "Status"
            message = "Check for Previous Messages: %s\n" % previous_message_check
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


def auto_receive():
    count = 0
    MYCURSOR.execute("SELECT username, address, private_key FROM accounts")
    myresult = MYCURSOR.fetchall()

    addresses = [str(result[1]) for result in myresult]
    private_keys = [str(result[2]) for result in myresult]
    MYDB.commit()
    pendings = get_pendings(addresses, threshold=nano_to_raw(PROGRAM_MINIMUM))
    # get any pending blocks from our address
    for address, private_key in zip(addresses, private_keys):
        # allow 5 transactions to be received per cycle. If the bot gets transaction spammed, at least it won't be
        # locked up receiving.
        if count >= 5:
            break
        try:
            if pendings["blocks"][address]:
                for sent_hash in pendings["blocks"][address]:
                    # address, private_key, dictionary where the blocks are the keys
                    open_or_receive_block(address, private_key, sent_hash)
                    count += 1
                    if count >= 2:
                        break

        except KeyError:
            pass
        except Exception as e:
            print(e)


def message_in_database(message):
    sql = "SELECT * FROM history WHERE comment_id = %s"
    val = (message.name,)
    MYCURSOR.execute(sql, val)
    results = MYCURSOR.fetchall()
    if len(results) > 0:
        LOGGER.info("Found previous messages: ")
        for result in results:
            LOGGER.info(result)
        return True
    return False


def check_inactive_transactions():
    t0 = time.time()
    LOGGER.info("Running inactive script")
    MYCURSOR.execute("SELECT username FROM accounts WHERE active IS NOT TRUE")
    myresults = MYCURSOR.fetchall()
    inactivated_accounts = {item[0] for item in myresults}

    MYCURSOR.execute(
        "SELECT recipient_username FROM history WHERE action = 'send' AND hash IS NOT NULL AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 31 DAY) AND (return_status = 'cleared' OR return_status = 'warned' OR return_status = 'return failed')"
    )
    results = MYCURSOR.fetchall()
    tipped_accounts = {item[0] for item in results}

    tipped_inactivated_accounts = inactivated_accounts.intersection(tipped_accounts)
    LOGGER.info(f"Accounts on warning: {sorted(tipped_inactivated_accounts)}")
    returns = {}
    # scrolls through our inactive members and check if they have unclaimed tips
    for i, result in enumerate(tipped_inactivated_accounts):
        # send warning messages on day 31
        sql = "SELECT * FROM history WHERE action = 'send' AND hash IS NOT NULL AND recipient_username = %s AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 31 DAY) AND return_status = 'cleared'"
        val = (result,)
        MYCURSOR.execute(sql, val)
        txns = MYCURSOR.fetchall()
        if len(txns) >= 1:
            LOGGER.info(f"Warning Message to {result}")

            message_recipient = result
            subject = "Please Activate Your Nano Tipper Account"
            message_text = "Somebody tipped you at least 30 days ago, but your account hasn't been activated yet.\n\nPlease activate your account by replying any command to this bot. If you do not, any tips 35 days or older will be returned.\n\n***\n\n"
            message_text += HELP
            sql = (
                "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
            )
            val = (message_recipient, subject, message_text)
            MYCURSOR.execute(sql, val)
            MYDB.commit()
            for txn in txns:
                sql = "UPDATE history SET return_status = 'warned' WHERE id = %s"
                val = (txn[0],)
                MYCURSOR.execute(sql, val)
                MYDB.commit()
            # print(message_recipient, subject, message_text)

        # return transactions over 35 days old
        sql = "SELECT * FROM history WHERE action = 'send' AND hash IS NOT NULL AND recipient_username = %s AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 35 DAY) AND return_status = 'warned'"
        val = (result,)
        MYCURSOR.execute(sql, val)
        txns = MYCURSOR.fetchall()
        if len(txns) >= 1:
            sql = "SELECT address, private_key FROM accounts WHERE username = %s"
            val = (result,)
            MYCURSOR.execute(sql, val)
            inactive_results = MYCURSOR.fetchall()
            address = inactive_results[0][0]
            private_key = inactive_results[0][1]

            for txn in txns:
                # set the pre-update message to 'return failed'. This will be changed to 'returned' upon success
                sql = "UPDATE history SET return_status = 'return failed' WHERE id = %s"
                val = (txn[0],)
                MYCURSOR.execute(sql, val)
                MYDB.commit()

                # get the transaction information and find out to whom we are returning the tip
                sql = "SELECT address, percentage FROM accounts WHERE username = %s"
                val = (txn[1],)
                MYCURSOR.execute(sql, val)
                returned_results = MYCURSOR.fetchall()
                recipient_address = returned_results[0][0]
                percentage = returned_results[0][1]
                percentage = float(percentage) / 100
                # print('History record: ', txn[0], address, private_key, txn[9], recipient_address)

                # send it back
                donation_amount = int(txn[9]) / 10 ** 30
                donation_amount = donation_amount * percentage
                donation_amount = nano_to_raw(donation_amount)

                return_amount = int(txn[9]) - donation_amount

                if (return_amount > 0) and (return_amount <= int(txn[9])):
                    hash = send(address, private_key, return_amount, recipient_address)[
                        "hash"
                    ]
                    add_history_record(
                        action="return",
                        hash=hash,
                        amount=return_amount,
                        notes="Returned transaction from history record %s" % txn[0],
                    )
                if (donation_amount > 0) and (donation_amount <= int(txn[9])):
                    hash2 = send(
                        address,
                        private_key,
                        donation_amount,
                        "xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij",
                    )["hash"]
                    add_history_record(
                        action="donate",
                        hash=hash2,
                        amount=donation_amount,
                        notes="Donation from returned tip %s" % txn[0],
                    )
                # print("Returning a transaction. ", hash)

                # update database if everything goes through
                sql = "UPDATE history SET return_status = 'returned' WHERE id = %s"
                val = (txn[0],)
                MYCURSOR.execute(sql, val)
                MYDB.commit()

                # add transactions to the messaging queue to build a single message
                message_recipient = txn[1]
                if message_recipient not in returns.keys():
                    returns[message_recipient] = {
                        "percent": round(percentage * 100, 2),
                        "transactions": [],
                    }
                returns[message_recipient]["transactions"].append(
                    [
                        result,
                        int(txn[9]) / 10 ** 30,
                        return_amount / 10 ** 30,
                        donation_amount / 10 ** 30,
                    ]
                )

                """
                # send a message informing the tipper that the tip is being returned
                message_recipient = txn[1]
                subject = 'Returned your tip of %s to %s' % (int(txn[9])/10**30, result)
                message_text = "Your tip to %s for %s Nano was returned since the user never activated their account, and %s percent of this was donated to the TipBot development fund. You can change this percentage by messaging the TipBot 'percentage <amount>', where <amount> is a number between 0 and 100." % (result, int(txn[9])/10**30, round(percentage*100, 2))
                sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
                val = (message_recipient, subject, message_text)
                MYCURSOR.execute(sql, val)
                MYDB.commit()
                """

        # return transactions over 35 days old, take two
        sql = "SELECT * FROM history WHERE action = 'send' AND hash IS NOT NULL AND recipient_username = %s AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 35 DAY) AND return_status = 'return failed'"
        val = (result,)
        MYCURSOR.execute(sql, val)
        txns = MYCURSOR.fetchall()
        if len(txns) >= 1:
            sql = "SELECT address, private_key FROM accounts WHERE username = %s"
            val = (result,)
            MYCURSOR.execute(sql, val)
            inactive_results = MYCURSOR.fetchall()
            address = inactive_results[0][0]
            private_key = inactive_results[0][1]

            for txn in txns:
                # set the pre-update message to 'return failed'. This will be changed to 'returned' upon success
                sql = (
                    "UPDATE history SET return_status = 'return failed2' WHERE id = %s"
                )
                val = (txn[0],)
                MYCURSOR.execute(sql, val)
                MYDB.commit()

                # get the transaction information and find out to whom we are returning the tip
                sql = "SELECT address, percentage FROM accounts WHERE username = %s"
                val = (txn[1],)
                MYCURSOR.execute(sql, val)
                returned_results = MYCURSOR.fetchall()
                recipient_address = returned_results[0][0]
                percentage = returned_results[0][1]
                percentage = float(percentage) / 100
                # print('History record: ', txn[0], address, private_key, txn[9], recipient_address)

                # send it back
                donation_amount = int(txn[9]) / 10 ** 30
                donation_amount = donation_amount * percentage
                donation_amount = nano_to_raw(donation_amount)

                return_amount = int(txn[9]) - donation_amount
                LOGGER.info("Returning transaction")
                if (return_amount > 0) and (return_amount <= int(txn[9])):
                    hash = send(address, private_key, return_amount, recipient_address)[
                        "hash"
                    ]
                    add_history_record(
                        action="return",
                        hash=hash,
                        amount=return_amount,
                        notes="Returned transaction from history record %s" % txn[0],
                    )
                LOGGER.info("Donating donation")
                if (donation_amount > 0) and (donation_amount <= int(txn[9])):
                    hash2 = send(
                        address,
                        private_key,
                        donation_amount,
                        "xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij",
                    )["hash"]
                    add_history_record(
                        action="donate",
                        hash=hash2,
                        amount=donation_amount,
                        notes="Donation from returned tip %s" % txn[0],
                    )
                # print("Returning a transaction. ", hash)

                # update database if everything goes through
                sql = "UPDATE history SET return_status = 'returned' WHERE id = %s"
                val = (txn[0],)
                MYCURSOR.execute(sql, val)
                MYDB.commit()

                # send a message informing the tipper that the tip is being returned
                message_recipient = txn[1]
                subject = "Returned your tip of %s to %s" % (
                    int(txn[9]) / 10 ** 30,
                    result,
                )
                message_text = (
                    "Your tip to %s for %s Nano was returned since the user never activated their account, and %s percent of this was donated to the TipBot development fund. You can change this percentage by messaging the TipBot 'percentage <amount>', where <amount> is a number between 0 and 100."
                    % (result, int(txn[9]) / 10 ** 30, round(percentage * 100, 2))
                )
                sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
                val = (message_recipient, subject, message_text)
                MYCURSOR.execute(sql, val)
                MYDB.commit()

        # send out our return messages
    for user in returns:
        message = (
            "The following tips have been returned and %s percent of each tip has been donated to the tipbot development fund:\n\n "
            "(Redditor, Total Tip Amount, Returned Amount, Donation Amount)\n\n "
            % returns[user]["percent"]
        )
        for transaction in returns[user]["transactions"]:
            message += "%s | %s | %s | %s\n\n " % (
                transaction[0],
                transaction[1],
                transaction[2],
                transaction[3],
            )
        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (user, "Returned Tips", message)
        MYCURSOR.execute(sql, val)
        MYDB.commit()
    LOGGER.info("Inactivated script complete.")


def main_loop():
    actions = {
        "message": handle_message,
        "comment": handle_comment,
        "username_mention": handle_comment,
        "faucet_tip": handle_message,
        "ignore": lambda x: None,
        "replay": lambda x: None,
        None: lambda x: None,
    }
    inactive_timer = time.time()
    receive_timer = time.time()
    check_inactive_transactions()
    for action_item in stream_comments_messages():
        action = parse_action(action_item)
        actions[action](action_item)

        # run the inactive script at the end of the loop; every 12 hours
        if time.time() - inactive_timer > 43200:
            inactive_timer = time.time()
            check_inactive_transactions()

        # run the receive script every 20 seconds
        if time.time() - receive_timer > 20:
            receive_timer = time.time()
            auto_receive()


def parse_action(action_item):
    if action_item is not None:
        parsed_text = parse_text(str(action_item.body))
    else:
        return None
    if message_in_database(action_item):
        return "prevented replay"
    elif not allowed_request(action_item.author, 30, 5):
        return "spam prevention"
    # check if it's a non-username post and if it has a tip or donate command
    elif action_item.name.startswith("t1_") and bool(
        {parsed_text[0], parsed_text[-2], parsed_text[-3]}
        & set(TIP_COMMANDS + DONATE_COMMANDS)
    ):
        LOGGER.info(f"Comment: {action_item.author} - " f"{action_item.body[:20]}")
        return "comment"
    # otherwise, lets parse the message. t4 means either a message or username mention
    elif action_item.name.startswith("t4_"):
        # check if it is a message from the bot.
        if action_item.author == TIP_BOT_USERNAME:
            # check if its a send, otherwise ignore
            if action_item.body.startswith("send 0.001 "):
                LOGGER.info(
                    f"Faucet Tip: {action_item.author} - {action_item.body[:20]}"
                )
                return "faucet_tip"
            else:
                return "ignore"
        # otherwise, check if it's a username mention
        elif bool(
            {parsed_text[0], parsed_text[-2]}
            & {"/u/%s" % TIP_BOT_USERNAME, "u/%s" % TIP_BOT_USERNAME}
        ):
            LOGGER.info(
                f"Username Mention: {action_item.author} - {action_item.body[:20]}"
            )
            return "username_mention"
        # otherwise, it's a normal message
        else:
            LOGGER.info(f"Comment: {action_item.author} - " f"{action_item.body[:20]}")
            return "message"
    return None


if __name__ == "__main__":
    main_loop()
