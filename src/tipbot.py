import time
import datetime
from time import sleep
from tipper_rpc import get_pendings, open_or_receive_block, send
import tipper_functions
from shared import (
    TIP_COMMANDS,
    LOGGER,
    MYCURSOR,
    MYDB,
    REDDIT,
    COMMENT_FOOTER,
    WELCOME_TIP,
    PROGRAM_MINIMUM,
    HELP,
    DONATE_COMMANDS,
    TIP_BOT_USERNAME,
    NEW_TIP,
)
from message_functions import (
    handle_message,
    add_history_record,
)
from tipper_functions import (
    check_balance,
    parse_text,
    send_pm,
    nano_to_raw,
    allowed_request,
    TipError,
    update_history_notes,
    account_info,
    add_new_account,
    parse_raw_amount,
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
    subreddits = "+".join(result[0] for result in results)
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
def handle_comment(message):

    response = send_from_comment(message)

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
        message.reply(response + COMMENT_FOOTER)
    # otherwise, if the subreddit is friendly (and reply is not top level) or subreddit is minimal
    elif subreddit_status in ["friendly", "minimal", "full"]:
        message.reply(response + COMMENT_FOOTER)
    elif subreddit_status in ["hostile", "silent"]:
        # it's a hostile place, no posts allowed. Will need to PM users
        message_recipient = str(message.author)
        subject = "Your Nano Tip Status"
        message_text = response + COMMENT_FOOTER
        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (message_recipient, subject, message_text)
        MYCURSOR.execute(sql, val)
        MYDB.commit()
    elif subreddit_status == "custom":
        # not sure what to do with this yet.
        pass


def send_from_comment(message):
    """
        Extracts send command information from a PM command
        :param message:
        :return: response string
        """
    new_account = True
    parsed_text = parse_text(str(message.body))

    # check if it's a donate command at the end
    if parsed_text[-3] in DONATE_COMMANDS:
        parsed_text = parsed_text[-3:]
    # check if it's a send command at the end
    if parsed_text[-2] in TIP_COMMANDS:
        parsed_text = parsed_text[-2:]
    username = str(message.author)

    message_time = datetime.datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    entry_id = add_history_record(
        username=username,
        action="send",
        comment_or_message="comment",
        comment_id=message.name,
        reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
        comment_text=str(message.body)[:255],
    )

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

    # check if amount is above subreddit minimum
    sql = "SELECT status FROM subreddits WHERE subreddit=%s"
    val = (str(message.subreddit).lower(),)
    MYCURSOR.execute(sql, val)
    results = MYCURSOR.fetchall()
    MYDB.commit()
    if len(results) == 0:
        subreddit_minimum = 1
    elif results[0][0] in ["friendly", "minimal", "silent"]:
        subreddit_minimum = 0
    else:
        subreddit_minimum = 1
    if amount < nano_to_raw(subreddit_minimum):
        update_history_notes(entry_id, "amount below subreddit minimum")
        response = (
            "To tip in unfamiliar subreddits, the tip amount must be 1 Nano or more. You attempted to tip %s Nano"
            % (amount / 10 ** 30)
        )
        return response

    # check the user's balance
    if amount > sender["balance"]:
        update_history_notes(entry_id, "insufficient funds")
        response = "You have insufficient funds. Please check your balance."
        return response

    # if it's a normal send, pull the account author
    # we will distinguish users from donations by the presence of a private key
    if parsed_text[0] in TIP_COMMANDS:
        try:
            recipient = account_info(str(message.author))
            new_account = False
        except TipError:
            recipient = add_new_account(recipient["username"])
            new_account = True
    elif parsed_text[0] in DONATE_COMMANDS:
        results = MYCURSOR.execute(
            "FROM projects SELECT address WHERE project = %s", (parsed_text[2],)
        )
        if len(results) <= 0:
            return "No Nanocenter project named %s was found." % parsed_text[2]
        recipient = {
            "username": parsed_text[2],
            "address": results[0][0],
            "minimum": -1,
        }
    else:
        return "Something strange happened."

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

    # send the nanos!!
    sent = send(sender["address"], sender["private_key"], amount, recipient["address"])

    # Update the sql and send the PMs
    sql = (
        "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, "
        "recipient_address = %s, amount = %s, return_status = %s WHERE id = %s"
    )
    val = (
        "sent to user",
        sender["address"],
        sender["username"],
        recipient["username"],
        recipient["address"],
        str(amount),
        "cleared",
        entry_id,
    )
    MYCURSOR.execute(sql, val)
    MYDB.commit()
    LOGGER.info(
        f"Sending Nano: {sender['address']} {sender['private_key']} {amount} {recipient['address']} {recipient['username']}"
    )

    # Update the sql and send the PMs if needed
    if "private_key" not in recipient.keys():
        sql = "UPDATE history SET notes = %s, address = %s, username = %s, recipient_address = %s, amount = %s WHERE id = %s"
        val = (
            "sent to nanocenter address",
            sender["address"],
            username,
            recipient["address"],
            str(amount),
            entry_id,
        )
        MYCURSOR.execute(sql, val)
        MYDB.commit()
        return (
            "Donated ```%.4g Nano``` to Nanocenter Project %s -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)"
            % (amount / 10 ** 30, recipient["username"], sent["hash"])
        )

    # update the sql database and send
    sql = (
        "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, "
        "recipient_address = %s, amount = %s, return_status = %s WHERE id = %s"
    )
    val = (
        "sent to user",
        sender["address"],
        sender["username"],
        recipient["username"],
        recipient["address"],
        str(amount),
        "cleared",
        entry_id,
    )
    MYCURSOR.execute(sql, val)
    MYDB.commit()
    if new_account:
        subject = "Congrats on receiving your first Nano Tip!"
        message_text = (
            WELCOME_TIP
            % (amount / 10 ** 30, recipient["address"], recipient["address"])
            + COMMENT_FOOTER
        )
        send_pm(recipient["username"], subject, message_text)
        return (
            "Creating a new account for /u/%s and "
            "sending ```%.4g Nano```. [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)"
            % (recipient["username"], amount / 10 ** 30, sent["hash"])
        )
    else:
        if not recipient["silence"]:
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
            send_pm(recipient["username"], subject, message_text)
        return (
            "Sent ```%.4g Nano``` to /u/%s -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)"
            % (amount / 10 ** 30, recipient["username"], sent["hash"])
        )


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
    subreddit_timer = time.time()
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

        # refresh subreddit status every 5 minutes
        if time.time() - subreddit_timer > 300:
            global SUBREDDITS
            subreddit_timer = time.time()
            SUBREDDITS = get_subreddits()


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
