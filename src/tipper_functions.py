import time
import requests
import json
from datetime import datetime
from shared import MYCURSOR, MYDB, RECIPIENT_MINIMUM, EXCLUDED_REDDITORS
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
            return super().__getitem__(name)
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
    return address


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


def account_info(username=None, address=None):
    """
    Pulls the address, private key and balance from a user
    :param username: string - redditors username
    :return: dict - name, address, private_key, balance
    """
    if username:
        sql = "SELECT address, private_key, minimum, silence FROM accounts WHERE username=%s"
        val = (username,)
    elif address:
        sql = "SELECT address, private_key, minimum, silence FROM accounts WHERE address=%s"
        val = (address,)
    else:
        raise UserWarning("You must specify a username or an address.")
    MYCURSOR.execute(sql, val)
    result = MYCURSOR.fetchall()
    if len(result) < 1:
        if username:
            raise TipError("user does not exist", "user does not exist")
        else:
            return {
                "username": None,
                "address": address,
                "private_key": None,
                "minimum": -1,
                "silence": False,
                "balance": None,
                "account_exists": False,
            }
    else:
        return {
            "username": username,
            "address": result[0][0],
            "private_key": result[0][1],
            "minimum": int(result[0][2]),
            "silence": result[0][3],
            "balance": check_balance(result[0][0])[0],
            "account_exists": True,
        }


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
    # check if there was a mistyped currency conversion i.e. "send 1 USD zily88" or
    # "!ntip 1 USD great jorb"
    # regardless of it being a message or a donate command, the actual amount will
    # always be at [1]

    if parsed_text[2].lower() in EXCLUDED_REDDITORS:
        raise TipError(
            "conversion syntax error",
            "It wasn't clear if you were trying to perform a currency conversion or not. If so, be sure there is no space between the amount and currency. Example: '!ntip 0.5USD'",
        )
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
