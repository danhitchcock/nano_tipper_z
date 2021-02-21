import time
import requests
import json
from datetime import datetime
from shared import (
    MYCURSOR,
    MYDB,
    RECIPIENT_MINIMUM,
    EXCLUDED_REDDITORS,
    TIP_BOT_USERNAME,
    LOGGER,
    TIP_COMMANDS,
    DONATE_COMMANDS,
    TIPBOT_DONATION_ADDRESS,
    REDDIT,
    STATUS_POST_ID,
    to_raw,
    from_raw,
)

from text import HELP, RETURN_WARNING, SUBJECTS

from tipper_rpc import generate_account, check_balance, send
from tipper_sql import list_subreddits
import text
import shared


def add_history_record(
    username=None,
    action=None,
    sql_time=None,
    address=None,
    comment_or_message=None,
    recipient_username=None,
    recipient_address=None,
    amount=None,
    hash=None,
    comment_id=None,
    notes=None,
    reddit_time=None,
    comment_text=None,
):
    if sql_time is None:
        sql_time = time.strftime("%Y-%m-%d %H:%M:%S")

    sql = (
        "INSERT INTO history (username, action, sql_time, address, comment_or_message, recipient_username, "
        "recipient_address, amount, hash, comment_id, notes, reddit_time, comment_text) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )

    val = (
        username,
        action,
        sql_time,
        address,
        comment_or_message,
        recipient_username,
        recipient_address,
        amount,
        hash,
        comment_id,
        notes,
        reddit_time,
        comment_text,
    )
    # todo make sure the rowid is atomic
    MYCURSOR.execute(sql, val)
    MYDB.commit()
    return MYCURSOR.lastrowid


def make_graceful(func):
    """
    Wrapper for inherited GracefulList methods that otherwise return a list
    100% unncecessary, only used for list __add__ at the moment
    """

    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if isinstance(res, list):
            return GracefulList(func(*args, **kwargs))
        else:
            return res

    return wrapper


class TipError(Exception):
    """
    General tiperror exception
    """

    def __init__(self, sql_text, response):
        self.sql_text = sql_text
        self.response = response


class GracefulList(list):
    """
    GracefulList is a list that returns None if there is an index error.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getitem__(self, name):
        try:
            if isinstance(name, int):
                return super().__getitem__(name)
            return GracefulList(super().__getitem__(name))
        except IndexError:
            return None

    @make_graceful
    def __add__(self, other):
        return super().__add__(other)


def parse_text(text):
    text = text.strip(" ")
    return GracefulList(text.lower().replace("\\", "").replace("\n", " ").split(" "))


def add_new_account(username):
    address = generate_account()
    private = address["private"]
    address = address["account"]
    sql = "INSERT INTO accounts (username, private_key, address, minimum, auto_receive, silence, active, percentage, opt_in) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    val = (
        username,
        private,
        address,
        to_raw(RECIPIENT_MINIMUM),
        True,
        False,
        False,
        10,
        True,
    )
    MYCURSOR.execute(sql, val)
    MYDB.commit()
    return {
        "username": username,
        "address": address,
        "private_key": private,
        "minimum": to_raw(RECIPIENT_MINIMUM),
        "silence": False,
        "balance": 0,
        "account_exists": True,
    }


def activate(author):
    sql = "UPDATE accounts SET active = TRUE WHERE username = %s"
    val = (str(author),)
    MYCURSOR.execute(sql, val)
    MYDB.commit()


def allowed_request(username, seconds=30, num_requests=5):
    """Spam prevention
    :param username: str (username)
    :param seconds: int (time period to allow the num_requests)
    :param num_requests: int (number of allowed requests)
    :return:
    """

    sql = "SELECT sql_time FROM history WHERE username=%s"
    val = (str(username),)
    MYCURSOR.execute(sql, val)
    myresults = MYCURSOR.fetchall()
    if len(myresults) < num_requests:
        return True
    else:
        return (
            datetime.fromtimestamp(time.time()) - myresults[-5][0]
        ).total_seconds() > seconds


def check_registered_by_address(address):
    address = address.split("_")[1]

    if shared.CURRENCY == "Nano":
        sql = "SELECT username FROM accounts WHERE address=%s"
        val = ("nano_" + address,)
        MYCURSOR.execute(sql, val)
        result = MYCURSOR.fetchall()
        if len(result) > 0:
            return result[0][0]

        sql = "SELECT username FROM accounts WHERE address=%s"
        val = ("xrb_" + address,)
        MYCURSOR.execute(sql, val)
        result = MYCURSOR.fetchall()
        if len(result) > 0:
            return result[0][0]
    elif shared.CURRENCY == "Banano":
        sql = "SELECT username FROM accounts WHERE address=%s"
        val = ("ban_" + address,)
        MYCURSOR.execute(sql, val)
        result = MYCURSOR.fetchall()
        if len(result) > 0:
            return result[0][0]
    return None


def get_user_settings(recipient_username, recipient_address=""):
    """

    :param recipient_username: str
    :param recipient_address: str
    :return: 3 items to unpack - int, str, bool
    """
    user_minimum = -1
    silence = False
    if recipient_username:
        sql = "SELECT minimum, address, silence FROM accounts WHERE username = %s"
        val = (recipient_username,)
        MYCURSOR.execute(sql, val)
        myresult = MYCURSOR.fetchall()
        if len(myresult) > 0:
            user_minimum = int(myresult[0][0])
            silence = myresult[0][2]
            if not recipient_address:
                recipient_address = myresult[0][1]
    return {
        "name": recipient_username,
        "minimum": user_minimum,
        "address": recipient_address,
        "silence": silence,
    }


def account_info(key, by_address=False):
    """
    Pulls the address, private key and balance from a user
    :param username: string - redditors username
    :return: dict - name, address, private_key, balance
    """
    if not by_address:
        sql = "SELECT username, address, private_key, minimum, silence, opt_in FROM accounts WHERE username=%s"
    else:
        sql = "SELECT username, address, private_key, minimum, silence, opt_in FROM accounts WHERE address=%s"
    val = (key,)
    result = query_sql(sql, val)
    if len(result) > 0:
        return {
            "username": result[0][0],
            "address": result[0][1],
            "private_key": result[0][2],
            "minimum": int(result[0][3]),
            "silence": result[0][4],
            "balance": check_balance(result[0][1])[0],
            "account_exists": True,
            "opt_in": result[0][5],
        }
    return None


def update_history_notes(entry_id, text):
    sql = "UPDATE history SET notes = %s WHERE id = %s"
    val = (text, entry_id)
    MYCURSOR.execute(sql, val)
    MYDB.commit()


def send_pm(recipient, subject, body, bypass_opt_out=False):
    opt_in = True
    # If there is not a bypass to opt in, check the status
    if not bypass_opt_out:
        sql = "SELECT opt_in FROM accounts WHERE username=%s"
        MYCURSOR.execute(sql, (recipient,))
        opt_in = MYCURSOR.fetchall()[0][0]
        MYDB.commit()

    # if the user has opted in, or if there is an override to send the PM even if they have not
    if opt_in or not bypass_opt_out:
        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (recipient, subject, body)
        MYCURSOR.execute(sql, val)
        MYDB.commit()


def parse_raw_amount(parsed_text, username=None):
    """
    Given some parsed command text, converts the units to Raw nano
    :param parsed_text:
    :param username: required if amount is 'all'
    :return:
    """
    conversion = 1
    # check if the amount is 'all'. This will convert it to the proper int
    if parsed_text[1].lower() == "all":
        sql = "SELECT address FROM accounts WHERE username = %s"
        val = (username,)
        MYCURSOR.execute(sql, val)
        result = MYCURSOR.fetchall()
        if len(result) > 0:
            address = result[0][0]
            balance = check_balance(address)
            return balance[0]
        else:
            raise (TipError(None, text.NOT_OPEN))

    # check if there is a currency code in the amount; if so, get the conversion
    if parsed_text[1][-3:].lower() in EXCLUDED_REDDITORS:
        currency = parsed_text[1][-3:].upper()
        url = "https://min-api.cryptocompare.com/data/price?fsym={}&tsyms={}".format(
            shared.CURRENCY, currency
        )
        try:
            results = requests.get(url, timeout=1)
            results = json.loads(results.text)
            conversion = float(results[currency])
            amount = parsed_text[1][:-3].lower()
        except requests.exceptions.Timeout:
            raise TipError(
                "Could not reach conversion server.",
                "Could not reach conversion server. Tip not sent.",
            )
        except:
            raise TipError(
                "Could not reach conversion server.",
                f"Currency {currency.upper()} not supported. Tip not sent.",
            )
    else:
        amount = parsed_text[1].lower()

    # before converting to a number, make sure the amount doesn't have nan or inf in it
    if amount == "nan" or ("inf" in amount):
        raise TipError(
            None,
            f"Could not read your tip or send amount. Is '{parsed_text[1]}' a number?",
        )
    else:
        try:
            amount = to_raw(float(amount) / conversion)
        except:
            raise TipError(
                None,
                f"Could not read your tip or send amount. Is '{amount}' a number, or is the "
                "currency code valid? If you are trying to send Nano directly, omit "
                "'Nano' from the amount (I will fix this in a future update).",
            )
    return amount


def parse_action(action_item):
    if action_item is not None:
        parsed_text = parse_text(str(action_item.body))
    else:
        return None
    if message_in_database(action_item):
        return "replay"
    elif not allowed_request(action_item.author, 30, 5):
        return "ignore"
    # check if it's a non-username post and if it has a tip or donate command
    elif action_item.name.startswith("t1_") and bool(
        {parsed_text[0], parsed_text[-2], parsed_text[-3]}
        & (
            set(TIP_COMMANDS + DONATE_COMMANDS).union(
                {"/u/%s" % TIP_BOT_USERNAME, "u/%s" % TIP_BOT_USERNAME}
            )
        )
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
        # otherwise, it's a normal message
        else:
            LOGGER.info(f"Comment: {action_item.author} - " f"{action_item.body[:20]}")
            return "message"
    return None


def message_in_database(message):
    sql = "SELECT * FROM history WHERE comment_id = %s"
    val = (message.name,)
    MYCURSOR.execute(sql, val)
    results = MYCURSOR.fetchall()
    if len(results) > 0:
        LOGGER.info("Found previous messages for %s: " % message.name)
        for result in results:
            LOGGER.info(result)
        return True
    return False


def exec_sql(sql, val):
    """
    Makes sql stuff easier to mock, rather than mocking execute and fetchall
    :param sql:
    :param val:
    :return:
    """
    MYCURSOR.execute(sql, val)
    MYDB.commit()


def query_sql(sql, val=None):
    if val:
        MYCURSOR.execute(sql, val)
    else:
        MYCURSOR.execute(sql)
    results = MYCURSOR.fetchall()
    MYDB.commit()
    return results


def return_transactions():
    LOGGER.info("Running inactive script")
    myresults = query_sql("SELECT username FROM accounts WHERE active IS NOT TRUE")
    inactivated_accounts = {item[0] for item in myresults}
    results = query_sql(
        "SELECT recipient_username FROM history WHERE action = 'send' "
        "AND hash IS NOT NULL "
        "AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 31 DAY) "
        "AND ("
        "return_status = 'cleared' "
        "OR return_status = 'warned'"
        ")"
    )
    tipped_accounts = {item[0] for item in results}
    tipped_inactivated_accounts = inactivated_accounts.intersection(tipped_accounts)
    LOGGER.info(f"Accounts on warning: {sorted(tipped_inactivated_accounts)}")
    returns = {}
    # scrolls through our inactive members and check if they have unclaimed tips
    for i, recipient in enumerate(tipped_inactivated_accounts):
        # send warning messages on day 31
        sql = (
            "SELECT id, username, amount FROM history WHERE action = 'send' "
            "AND hash IS NOT NULL "
            "AND recipient_username = %s "
            "AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 31 DAY) "
            "AND return_status = 'cleared'"
        )
        txns = query_sql(sql, (recipient,))
        if len(txns) >= 1:
            LOGGER.info(f"Warning Message to {recipient}")

            send_pm(recipient, SUBJECTS["RETURN_WARNING"], RETURN_WARNING + HELP)
            for txn in txns:
                sql = "UPDATE history SET return_status = 'warned' WHERE id = %s"
                val = (txn[0],)
                exec_sql(sql, val)

        # return transactions over 35 days old
        sql = (
            "SELECT id, username, amount FROM history WHERE action = 'send' "
            "AND hash IS NOT NULL "
            "AND recipient_username = %s "
            "AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 35 DAY) "
            "AND return_status = 'warned'"
        )
        val = (recipient,)
        txns = query_sql(sql, val)
        if len(txns) >= 1:
            sql = "SELECT address, private_key FROM accounts WHERE username = %s"
            inactive_results = query_sql(sql, (recipient,))
            address = inactive_results[0][0]
            private_key = inactive_results[0][1]

            for txn in txns:
                # set the pre-update message to 'return failed'. This will be changed
                # to 'returned' upon success
                sql = "UPDATE history SET return_status = 'return failed' WHERE id = %s"
                val = (txn[0],)
                exec_sql(sql, val)
                # get the transaction information and find out to whom we are returning
                # the tip
                sql = "SELECT address, percentage FROM accounts WHERE username = %s"
                val = (txn[1],)
                returned_results = query_sql(sql, val)
                recipient_address = returned_results[0][0]
                percentage = returned_results[0][1]
                percentage = float(percentage) / 100
                # send it back
                donation_amount = from_raw(int(txn[2]))
                donation_amount = donation_amount * percentage
                donation_amount = to_raw(donation_amount)

                return_amount = int(txn[2]) - donation_amount
                if (return_amount > 0) and (return_amount <= int(txn[2])):
                    hash = send(address, private_key, return_amount, recipient_address)[
                        "hash"
                    ]
                    add_history_record(
                        action="return",
                        hash=hash,
                        amount=return_amount,
                        notes="Returned transaction from history record %s" % txn[0],
                    )

                if (donation_amount > 0) and (donation_amount <= int(txn[2])):
                    hash2 = send(
                        address,
                        private_key,
                        donation_amount,
                        TIPBOT_DONATION_ADDRESS,
                    )["hash"]
                    add_history_record(
                        action="donate",
                        hash=hash2,
                        amount=donation_amount,
                        notes="Donation from returned tip %s" % txn[0],
                    )
                # update database if everything goes through
                sql = "UPDATE history SET return_status = 'returned' WHERE id = %s"
                val = (txn[0],)
                exec_sql(sql, val)
                # add transactions to the messaging queue to build a single message
                message_recipient = txn[1]
                if message_recipient not in returns.keys():
                    returns[message_recipient] = {
                        "percent": round(percentage * 100, 2),
                        "transactions": [],
                    }
                returns[message_recipient]["transactions"].append(
                    [
                        recipient,
                        from_raw(int(txn[2])),
                        from_raw(return_amount),
                        from_raw(donation_amount),
                    ]
                )

        # send out our return messages
    for user in returns:
        message = text.make_return_message(returns[user])
        send_pm(user, SUBJECTS["RETURN_MESSAGE"], message)
    LOGGER.info("Inactivated script complete.")


def update_status_message():
    subreddits = list_subreddits()
    body = "Current Subreddits: \n"
    body += "\n".join([", ".join([val for val in sub]) for sub in subreddits])
    submission = REDDIT.submission(STATUS_POST_ID)
    submission.edit(body)
