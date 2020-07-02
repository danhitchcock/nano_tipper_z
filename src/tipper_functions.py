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
)
from tipper_rpc import generate_account, nano_to_raw, check_balance


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
    sql = "INSERT INTO accounts (username, private_key, address, minimum, auto_receive, silence, active, percentage) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    val = (
        username,
        private,
        address,
        nano_to_raw(RECIPIENT_MINIMUM),
        True,
        False,
        False,
        10,
    )
    MYCURSOR.execute(sql, val)
    MYDB.commit()
    return {
        "username": username,
        "address": address,
        "private_key": private,
        "minimum": nano_to_raw(RECIPIENT_MINIMUM),
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
    """ Spam prevention
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
        sql = "SELECT username, address, private_key, minimum, silence FROM accounts WHERE username=%s"
    else:
        sql = "SELECT username, address, private_key, minimum, silence FROM accounts WHERE address=%s"
    val = (key,)
    result = query_sql(sql, val)
    if len(result) < 1:
        return {
            "username": result[0][0],
            "address": result[0][1],
            "private_key": result[0][2],
            "minimum": int(result[0][3]),
            "silence": result[0][4],
            "balance": check_balance(result[0][0])[0],
            "account_exists": True,
        }
    return None


def update_history_notes(entry_id, text):
    sql = "UPDATE history SET notes = %s WHERE id = %s"
    val = (text, entry_id)
    MYCURSOR.execute(sql, val)
    MYDB.commit()


def send_pm(recipient, subject, body):
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
            raise (
                TipError(None, 'You do not have a tip bot account yet. PM me "create".')
            )

    # check if there is a currency code in the amount; if so, get the conversion
    if parsed_text[1][-3:].lower() in EXCLUDED_REDDITORS:
        currency = parsed_text[1][-3:].upper()
        url = "https://min-api.cryptocompare.com/data/price?fsym={}&tsyms={}".format(
            "NANO", currency
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
            amount = nano_to_raw(float(amount) / conversion)
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


def message_in_database(message):
    sql = "SELECT * FROM history WHERE comment_id = %s"
    val = (message.name,)
    print("this is a tipper message in database")
    MYCURSOR.execute(sql, val)
    results = MYCURSOR.fetchall()
    if len(results) > 0:
        LOGGER.info("Found previous messages: ")
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


def query_sql(sql, val):
    MYCURSOR.execute(sql, val)
    results = MYCURSOR.fetchall()
    MYDB.commit()
    return results
