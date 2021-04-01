from datetime import datetime
from shared import (
    TIP_BOT_USERNAME,
    LOGGER,
    TIP_COMMANDS,
    to_raw,
    History,
    Account,
    Message
)

from text import SUBJECTS

from tipper_rpc import generate_account, check_balance, send
import text
import shared


def add_history_record(
    username=None,
    action="unknown",
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
    if action is None:
        action = "unknown"
    if reddit_time is None:
        reddit_time=datetime.utcnow()
    history = History(
        username=username,
        action=action,
        address=address,
        comment_or_message=comment_or_message,
        recipient_username=recipient_username,
        recipient_address=recipient_address,
        amount=amount,
        hash=hash,
        comment_id=comment_id,
        notes=notes,
        reddit_time=reddit_time,
        comment_text=comment_text
        
    )

    if history.save() < 1:
        LOGGER.error(f"Failed saving history item {username}")

    return history.id


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
    address, pk = generate_account()
    if address is None:
        LOGGER.error("Failed to create account!")
        return None
    acct = Account(
        username=username,
        private_key=pk,
        address=address,
        silence=False,
        active=False,
        opt_in=True
    )
    acct.save(force_insert=True)
    return {
        "username": username,
        "address": address,
        "private_key": pk,
        "silence": False,
        "balance": 0,
        "account_exists": True,
    }


def activate(author):
    Account.update(active=True).where(Account.username == str(author)).execute()

def allowed_request(username, seconds=30, num_requests=5):
    """Spam prevention
    :param username: str (username)
    :param seconds: int (time period to allow the num_requests)
    :param num_requests: int (number of allowed requests)
    :return:
    """
    historyQ = History.select(History.sql_time).where(History.username == str(username)).order_by(History.id)
    history_list = [h for h in historyQ]
    if len(history_list) < num_requests:
        return True
    else:
        i = 0
        for h in history_list:
            i+=1
            if i == 5:
                return (
                    datetime.utcnow() - h.sql_time
                ).total_seconds() > seconds


def check_registered_by_address(address):
    address = address.split("_")[1]

    if shared.CURRENCY == "Nano":
        try:
            acct = Account.get(address=f"nano_{address}")
            return acct.address
        except Account.DoesNotExist:
            pass

        try:
            acct = Account.get(address=f"xrb_{address}")
            return acct.address
        except Account.DoesNotExist:
            pass
    elif shared.CURRENCY == "Banano":
        try:
            acct = Account.get(address=f"ban_{address}")
            return acct.address
        except Account.DoesNotExist:
            pass

    return None


def get_user_settings(recipient_username, recipient_address=""):
    """

    :param recipient_username: str
    :param recipient_address: str
    :return: 3 items to unpack - int, str, bool
    """
    silence = False
    if recipient_username:
        try:
            acct = Account.select(Account.minimum, Account.address, Account.silence).where(Account.username == recipient_username).get()
            silence = acct.silence
            if not recipient_address:
                recipient_address = acct.address
        except Account.DoesNotExist:
            pass
    return {
        "name": recipient_username,
        "address": recipient_address,
        "silence": silence,
    }


def account_info(key, by_address=False):
    """
    Pulls the address, private key and balance from a user
    :param username: string - redditors username
    :return: dict - name, address, private_key, balance
    """
    foundAccount = True
    if not by_address:
        try:
            acct = Account.select().where(Account.username == key).get()
        except Account.DoesNotExist:
            foundAccount = False
    else:
        try:
            acct = Account.select().where(Account.address == key).get()
        except Account.DoesNotExist:
            foundAccount = False
    if foundAccount:
        return {
            "username": acct.username,
            "address": acct.address,
            "private_key": acct.private_key,
            "silence": acct.silence,
            "balance": check_balance(acct.address),
            "account_exists": True,
            "opt_in": acct.opt_in,
        }
    return None


def update_history_notes(entry_id, text):
    History.update(notes=text).where(History.id == entry_id).execute()


def send_pm(recipient, subject, body, bypass_opt_out=False):
    opt_in = True
    # If there is not a bypass to opt in, check the status
    if not bypass_opt_out:
        try:
            acct = Account.select(Account.opt_in).where(Account.username == recipient).get()
            opt_in = acct.opt_in
        except Account.DoesNotExist:
            pass
    # if the user has opted in, or if there is an override to send the PM even if they have not
    if opt_in or not bypass_opt_out:
        msg = Message(
            username = recipient,
            subject = subject,
            message = body
        )
        msg.save()


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
        try:
            acct = Account.select(Account.address).where(Account.username == username).get()
            address = acct.address
            balance = check_balance(address)
            return balance
        except Account.DoesNotExist:
            raise (TipError(None, text.NOT_OPEN))

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
            set(TIP_COMMANDS).union(
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
    query = History.select().where(History.comment_id == message.name)
    results = [r for r in query]
    if len(results) > 0:
        LOGGER.info("Found previous messages for %s: " % message.name)
        return True
    return False