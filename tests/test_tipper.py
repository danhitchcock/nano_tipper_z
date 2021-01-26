import types
import time
import shared


# It is important to only import shared before disabling the database.
# Otherwise, other tipper modules might import shared prior to the database
# being patched
class MockedCursor:
    def execute(self, sql, val=None):
        raise Exception("Hey, don't do that!")

    def fetchall(self):
        raise Exception("Hey, don't do that!")

    def MockedDB(self):
        raise Exception("Not sure how we got here, but no!")


class MockedDB:
    def commit(self):
        raise Exception("Hey, don't do that!")


shared.MYDB = MockedDB()
shared.MYCURSOR = MockedCursor()
shared.REDDIT = None
shared.SUBREDDITS = None
shared.DEFAULT_URL = None
import text
import tipbot
from tipbot import stream_comments_messages
import pytest
from shared import TIP_COMMANDS, TIP_BOT_USERNAME, to_raw
import message_functions
from message_functions import handle_send
import comment_functions
from comment_functions import send_from_comment
from tipper_functions import TipError
import tipper_functions


class RedditMessage:
    def __init__(
        self,
        name="",
        author="",
        subject="",
        body="",
        created_utc=time.time(),
        subreddit="friendly_sub",
        parent_id="t3_",
        parent_author=None,
    ):
        self.name = name
        self.author = author
        self.body = body
        self.subject = subject
        self.created_utc = created_utc
        self.subreddit = subreddit
        self.parent_id = parent_id
        self.parent_author = parent_author

    def parent(self):
        return type(self)(author=self.parent_author)


def test_graceful_list():
    a = tipper_functions.GracefulList([1, 2, 3, 4])
    assert a[0] == 1
    assert a[4] is None
    assert (a + [4])[5] is None
    a = a[:2]

    assert a[4] is None


def mock_account_info(key, by_address=False):
    balances = {
        "rich": {
            "username": "rich",
            "address": "private",
            "private_key": "one",
            "minimum": 0,
            "silence": False,
            "balance": to_raw(100),
            "account_exists": True,
            "opt_in": True,
        },
        "poor": {
            "username": "poor",
            "address": "private",
            "private_key": "one",
            "minimum": 0,
            "silence": False,
            "balance": 0,
            "account_exists": True,
            "opt_in": True,
        },
        "high_min": {
            "username": "high_min",
            "address": "private",
            "private_key": "one",
            "minimum": to_raw(100),
            "silence": False,
            "balance": 0,
            "account_exists": True,
            "opt_in": True,
        },
        "nano_valid": {
            "username": None,
            "address": "valid",
            "private_key": None,
            "minimum": -1,
            "silence": False,
            "balance": None,
            "account_exists": False,
            "opt_in": True,
        },
        "silent": {
            "username": "high_min",
            "address": "private",
            "private_key": "one",
            "minimum": to_raw(100),
            "silence": True,
            "balance": 0,
            "account_exists": True,
            "opt_in": True,
        },
        "out": {
            "username": "rich",
            "address": "private",
            "private_key": "one",
            "minimum": 0,
            "silence": False,
            "balance": to_raw(100),
            "account_exists": True,
            "opt_in": False,
        },
    }
    if not by_address:
        try:
            return balances[key]
        except KeyError:
            return None
    # implement return address


def mock_message_in_database(username):
    return False


def mock_allowed_request(username, time_limit, message_limit):
    return True


@pytest.fixture
def parse_action_mocks(monkeypatch):
    monkeypatch.setattr(
        tipper_functions, "message_in_database", mock_message_in_database
    )
    monkeypatch.setattr(tipper_functions, "allowed_request", mock_allowed_request)


def mock_parse_recipient_username(recipient_text):
    if recipient_text[:3].lower() == "/u/":
        recipient_text = recipient_text[3:]
    elif recipient_text[:2].lower() == "u/":
        recipient_text = recipient_text[2:]

    if recipient_text == "nano_valid":
        return {"address": "nano_valid"}
    if recipient_text == "nano_invalid":
        raise TipError(
            "invalid address or address-like redditor does not exist",
            "%s is neither a valid address nor a redditor" % recipient_text,
        )
    if recipient_text == "does_not_exist":
        raise TipError(
            "redditor does not exist",
            "Could not find redditor %s. Make sure you aren't writing or "
            "copy/pasting markdown." % recipient_text,
        )
    return {"username": recipient_text}


def mock_query_sql(sql, val=None):
    # subreddits
    if sql == "SELECT status, minimum FROM subreddits WHERE subreddit=%s":
        val = val[0]
        vals = {
            "friendly_sub": [["full", ".001"]],
            "minimal_sub": [["minimal", ".001"]],
            "hostile_sub": [["silent", "1"]],
            "not_tracked_sub": [],
        }
        return vals[val]
    if sql == "FROM projects SELECT address WHERE project = %s":
        val = val[0]
        vals = {
            "project_exists": [["address"]],
            "project_does_not_exist": [],
        }
        return vals[val]

    # return script
    if sql == "SELECT username FROM accounts WHERE active IS NOT TRUE":
        return [["return_me"], ["warn_me"]]
    if sql == (
        "SELECT recipient_username FROM history WHERE action = 'send' "
        "AND hash IS NOT NULL "
        "AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 31 DAY) "
        "AND ("
        "return_status = 'cleared' "
        "OR return_status = 'warned'"
        ")"
    ):
        return [["warn_me"], ["return_me"]]
    if sql == (
        "SELECT id, username, amount FROM history WHERE action = 'send' "
        "AND hash IS NOT NULL "
        "AND recipient_username = %s "
        "AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 31 DAY) "
        "AND return_status = 'cleared'"
    ):
        if val[0] == "warn_me":
            return [[1, "warn_me", "1000000000000000000000000000"]]
        else:
            return []
    if sql == (
        "SELECT id, username, amount FROM history WHERE action = 'send' "
        "AND hash IS NOT NULL "
        "AND recipient_username = %s "
        "AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 35 DAY) "
        "AND return_status = 'warned'"
    ):
        if val[0] == "return_me":
            return [[1, "return_me", "1000000000000000000000000000"]]
        else:
            return []
    if sql == ("SELECT address, private_key FROM accounts WHERE username = %s"):
        val = val[0]
        vals = {"warn_me": [["one", "two"]], "return_me": [["one", "two"]]}
        return vals[val]
    if sql == ("SELECT address, percentage FROM accounts WHERE username = %s"):
        val = val[0]
        vals = {"warn_me": [["one", 50]], "return_me": [["one", 50]]}
        return vals[val]
    raise Exception("Unhandled sql query")


def mock_add_new_account(username):
    return {
        "username": username,
        "address": "valid",
        "private_key": "private",
        "minimum": 0,
        "silence": False,
        "balance": 0,
        "account_exists": False,
    }


def test_parse_action(parse_action_mocks):
    tests = [
        (
            "comment",
            RedditMessage("t1_1", "daniel", "", f"{TIP_COMMANDS[0]} .1"),
        ),
        (
            "comment",
            RedditMessage("t1_2", "daniel", "", f"great job {TIP_COMMANDS[0]} .1"),
        ),
        (
            "comment",
            RedditMessage("t1_3", "daniel", "", f"/u/{TIP_BOT_USERNAME} .1"),
        ),
        (
            "comment",
            RedditMessage("t1_4", "daniel", "", f"nice /u/{TIP_BOT_USERNAME} .1"),
        ),
        (
            "message",
            RedditMessage("t4_5", "daniel", "", "history"),
        ),
        (
            "faucet_tip",
            RedditMessage("t4_6", "nano_tipper_z", "", "send 0.001 someone"),
        ),
    ]

    for test in tests:
        assert test[0] == tipper_functions.parse_action(test[1])


@pytest.fixture
def handle_send_from_message_mocks(monkeypatch):
    monkeypatch.setattr(tipper_functions, "account_info", mock_account_info)
    monkeypatch.setattr(
        message_functions, "add_history_record", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        tipper_functions,
        "add_new_account",
        mock_add_new_account,
    )
    monkeypatch.setattr(message_functions, "update_history_notes", lambda *args: None)
    monkeypatch.setattr(
        message_functions, "parse_recipient_username", mock_parse_recipient_username
    )

    monkeypatch.setattr(tipper_functions, "exec_sql", lambda *args: None)
    monkeypatch.setattr(message_functions, "send", lambda *args: {"hash": "success!"})
    monkeypatch.setattr(message_functions, "send_pm", lambda *args: None)
    monkeypatch.setattr(message_functions, "check_balance", lambda *args: [0, 0])


def test_handle_send_from_PM(handle_send_from_message_mocks):
    """
    Error codes:
    Success
    10 - sent to existing user
    20 - sent to new user
    30 - sent to address
    40 - donated to nanocenter project
    Tip not sent
    100 - sender account does not exist
    110 - Amount and/or recipient not specified
    120 - could not parse send amount
    130 - below program minimum
    140 - currency code issue
    150 - below 1 nano for untracked sub
    160 - insufficient funds
    170 - invalid address / recipient
    180 - below recipient minimum
    190 - user has opted out
    200 - No Nanocenter Project specified
    210 - Nanocenter Project does not exist
    """
    # sender has no account
    message = RedditMessage("t4_5", "DNE", "", "send 0.01 poor")
    response = handle_send(message)
    assert response == {"status": 100, "username": "DNE"}
    assert (
        text.make_response_text(message, response)
        == "You don't have an account yet. Please PM me with `create` in the body to make an account."
    )
    # no recipient specified
    message = RedditMessage("t4_5", "rich", "", "send 0.01")
    response = handle_send(message)
    assert response == {"status": 110, "username": "rich"}
    assert (
        text.make_response_text(message, response)
        == "You must specify an amount and a user, e.g. `send 1 nano_tipper`."
    )
    # no amount or recipient specified
    message = RedditMessage("t4_5", "rich", "", "send")
    response = handle_send(message)
    assert response == {"status": 110, "username": "rich"}
    assert (
        text.make_response_text(message, response)
        == "You must specify an amount and a user, e.g. `send 1 nano_tipper`."
    )

    # could not parse the amount
    message = RedditMessage("t4_5", "rich", "", "send 0.0sdf1 poor")
    response = handle_send(message)
    assert response == {
        "amount": "0.0sdf1",
        "status": 120,
        "username": "rich",
    }
    assert (
        text.make_response_text(message, response)
        == "I could not read the amount or the currency code. Is '0.0sdf1' a number? This could also mean the currency converter is down."
    )

    # send below sender balance
    message = RedditMessage("t4_5", "poor", "", "send 0.01 rich")
    response = handle_send(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "status": 160,
        "username": "poor",
    }
    assert (
        text.make_response_text(message, response)
        == "You have insufficient funds. Please check your balance."
    )

    # send send to opted out user
    message = RedditMessage("t4_5", "rich", "", "send 0.01 out")
    response = handle_send(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "status": 190,
        "username": "rich",
        "recipient": "out",
    }
    assert (
        text.make_response_text(message, response)
        == "Sorry, the user has opted-out of using Nano Tipper."
    )

    # send to an Excluded redditor (i.e. a currency code)
    message = RedditMessage("t4_5", "rich", "", "send 0.01 USD rich")
    response = handle_send(message)
    assert response == {
        "status": 140,
        "username": "rich",
    }
    assert (
        text.make_response_text(message, response)
        == "It wasn't clear if you were trying to perform a currency conversion o"
        "r not. If so, be sure there is no space between the amount and currency. "
        "Example: '!ntip 0.5USD'"
    )

    # send below user minimum
    message = RedditMessage("t4_5", "rich", "", "send 0.01 high_min")
    response = handle_send(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "minimum": 100000000000000000000000000000000,
        "recipient": "high_min",
        "status": 180,
        "username": "rich",
    }
    assert (
        text.make_response_text(message, response)
        == "Sorry, the user has set a tip minimum of 100.0. Your tip of 0.01 is "
        "below this amount."
    )

    # send below program limit
    message = RedditMessage("t4_5", "rich", "", "send 0.00001 high_min")
    response = handle_send(message)
    assert response == {
        "amount": 10000000000000000000000000,
        "status": 130,
        "username": "rich",
    }
    assert (
        text.make_response_text(message, response) == "Program minimum is 0.0001 Nano."
    )

    # send to invalid address/not a redditor
    message = RedditMessage("t4_5", "rich", "", "send 0.01 nano_invalid")
    response = handle_send(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "recipient": "nano_invalid",
        "status": 170,
        "username": "rich",
    }
    assert (
        text.make_response_text(message, response)
        == "'nano_invalid' is neither a redditor nor a valid address."
    )

    # send to valid account
    message = RedditMessage("t4_5", "rich", "", "send 0.01 poor")
    response = handle_send(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "recipient": "poor",
        "status": 10,
        "username": "rich",
        "hash": "success!",
    }
    assert (
        text.make_response_text(message, response)
        == "Sent ```0.01 Nano``` to /u/poor -- [Transaction on Nano Crawler](https:"
        "//nanocrawler.cc/explorer/block/success!)"
    )

    # send to new account
    message = RedditMessage("t4_5", "rich", "", "send 0.01 DNE")
    response = handle_send(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "recipient": "dne",
        "status": 20,
        "username": "rich",
        "hash": "success!",
    }
    assert (
        text.make_response_text(message, response)
        == "Creating a new account for /u/dne and sending ```0.01 Nano```. [Transac"
        "tion on Nano Crawler](https://nanocrawler.cc/explorer/block/success!)"
    )

    # send to valid address
    message = RedditMessage("t4_5", "rich", "", "send 0.01 nano_valid")
    response = handle_send(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "recipient": "nano_valid",
        "status": 30,
        "username": "rich",
        "hash": "success!",
    }
    assert (
        text.make_response_text(message, response)
        == "Sent ```0.01 Nano``` to address nano_valid -- [Transaction on Nano Cra"
        "wler](https://nanocrawler.cc/explorer/block/success!)"
    )


@pytest.fixture
def handle_send_from_comment_mocks(monkeypatch):
    monkeypatch.setattr(tipper_functions, "account_info", mock_account_info)
    monkeypatch.setattr(
        comment_functions, "add_history_record", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(tipper_functions, "add_new_account", mock_add_new_account)
    monkeypatch.setattr(comment_functions, "update_history_notes", lambda *args: None)
    monkeypatch.setattr(tipper_functions, "query_sql", mock_query_sql)
    monkeypatch.setattr(tipper_functions, "exec_sql", lambda *args: None)
    monkeypatch.setattr(comment_functions, "send", lambda *args: {"hash": "success!"})
    monkeypatch.setattr(comment_functions, "send_pm", lambda *args: None)
    monkeypatch.setattr(comment_functions, "check_balance", lambda *args: [0, 0])


def test_handle_send_from_comment_and_text(handle_send_from_comment_mocks):
    """
    Error codes:
    Success
    10 - sent to existing user
    20 - sent to new user
    30 - sent to address
    40 - donated to nanocenter project
    Tip not sent
    100 - sender account does not exist
    110 - Amount and/or recipient not specified
    120 - could not parse send amount
    130 - below program minimum
    140 - currency code issue
    150 - below 1 nano for untracked sub
    160 - insufficient funds
    170 - invalid address / recipient
    180 - below recipient minimum
    200 - No Nanocenter Project specified
    210 - Nanocenter Project does not exist
    """

    # sender has no account
    message = RedditMessage("t4_5", "DNE", "", f"{TIP_COMMANDS[0]} 0.01")
    response = send_from_comment(message)
    assert response == {
        "status": 100,
        "username": "DNE",
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response)
        == "You don't have an account yet. Please PM me with `create` in the body to make an account."
    )

    # no amount specified
    message = RedditMessage("t4_5", "rich", "", f"{TIP_COMMANDS[0]}")
    response = send_from_comment(message)
    assert response == {
        "status": 110,
        "username": "rich",
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response)
        == "You must specify an amount and a user, e.g. `send 1 nano_tipper`."
    )

    # could not parse the amount
    message = RedditMessage("t4_5", "rich", "", f"{TIP_COMMANDS[0]} 0.0sdf1")
    response = send_from_comment(message)
    assert response == {
        "status": 120,
        "username": "rich",
        "amount": "0.0sdf1",
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response)
        == "I could not read the amount or the currency code. Is '0.0sdf1' a number? This could also mean the currency converter is down."
    )
    # send below program limit
    message = RedditMessage("t4_5", "rich", "", f"{TIP_COMMANDS[0]} 0.00001")
    response = send_from_comment(message)
    assert response == {
        "amount": 10000000000000000000000000,
        "status": 130,
        "username": "rich",
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response) == "Program minimum is 0.0001 Nano."
    )

    # send to an Excluded redditor (i.e. a currency code)
    message = RedditMessage("t4_5", "rich", "", f"{TIP_COMMANDS[0]} 0.01 USD")
    response = send_from_comment(message)
    assert response == {
        "status": 140,
        "username": "rich",
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response)
        == "It wasn't clear if you were trying to perform a currency conversion or "
        "not. If so, be sure there is no space between the amount and currency. "
        "Example: '!ntip 0.5USD'"
    )

    # subreddit is not tracked
    message = RedditMessage(
        "t4_5", "rich", "", f"/u/{TIP_BOT_USERNAME} 0.01", subreddit="not_tracked_sub"
    )
    response = send_from_comment(message)
    assert response == {
        "status": 150,
        "amount": 10000000000000000000000000000,
        "subreddit_minimum": 1,
        "username": "rich",
        "subreddit": "not_tracked_sub",
        "subreddit_status": "untracked",
    }
    assert (
        text.make_response_text(message, response)
        == "Your tip is below the minimum for an unfamiliar sub."
    )

    # send greater than sender balance
    message = RedditMessage(
        "t4_5", "poor", "", f"{TIP_COMMANDS[0]} 0.01", subreddit="friendly_sub"
    )
    response = send_from_comment(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "status": 160,
        "username": "poor",
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response)
        == "You have insufficient funds. Please check your balance."
    )

    # user is opted out
    message = RedditMessage(
        "t4_5",
        "rich",
        "",
        f"{TIP_COMMANDS[0]} 0.01",
        subreddit="friendly_sub",
        parent_author="out",
    )
    response = send_from_comment(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "status": 190,
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "username": "rich",
        "recipient": "out",
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response)
        == "Sorry, the user has opted-out of using Nano Tipper."
    )

    # send less than recipient minimum
    message = RedditMessage(
        "t4_5",
        "rich",
        "",
        f"{TIP_COMMANDS[0]} 0.01",
        subreddit="friendly_sub",
        parent_author="high_min",
    )
    response = send_from_comment(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "minimum": 100000000000000000000000000000000,
        "status": 180,
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "subreddit_status": "full",
        "username": "rich",
        "recipient": "high_min",
    }
    assert (
        text.make_response_text(message, response)
        == "Sorry, the user has set a tip minimum of 100.0. Your tip of 0.01 is below this amount."
    )

    # send to new user
    message = RedditMessage(
        "t4_5",
        "rich",
        "",
        f"{TIP_COMMANDS[0]} 0.01",
        subreddit="friendly_sub",
        parent_author="dne",
    )
    response = send_from_comment(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "status": 20,
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "subreddit_status": "full",
        "username": "rich",
        "hash": "success!",
        "recipient": "dne",
    }
    assert (
        text.make_response_text(message, response)
        == "Creating a new account for /u/dne and sending ```0.01 Nano```. [Transac"
        "tion on Nano Crawler](https://nanocrawler.cc/explorer/block/success!)"
    )
    # check text for minimal
    message.subreddit = "minimal_sub"
    response = send_from_comment(message)
    assert (
        text.make_response_text(message, response)
        == "^(Made a new account and )^[sent](https://nanocrawler.cc/explorer/block"
        "/success!) ^0.01 ^Nano ^to ^(/u/dne) ^- [^(Nano Tipper)](https://githu"
        "b.com/danhitchcock/nano_tipper_z)"
    )

    # send to user
    message = RedditMessage(
        "t4_5",
        "rich",
        "",
        f"{TIP_COMMANDS[0]} 0.01",
        subreddit="friendly_sub",
        parent_author="poor",
    )
    response = send_from_comment(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "status": 10,
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "username": "rich",
        "hash": "success!",
        "recipient": "poor",
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response)
        == "Sent ```0.01 Nano``` to /u/poor -- [Transaction on Nano Crawler](https"
        "://nanocrawler.cc/explorer/block/success!)"
    )
    # minimal text for new user
    message.subreddit = "minimal_sub"
    response = send_from_comment(message)
    assert (
        text.make_response_text(message, response)
        == "^[Sent](https://nanocrawler.cc/explorer/block/success!) ^0.01 ^Nano "
        "^to ^(/u/poor) ^- [^(Nano Tipper)](https://github.com/danhitchcock/nan"
        "o_tipper_z)"
    )

    # send at end of message
    message = RedditMessage(
        "t4_5",
        "rich",
        "",
        f"something something {TIP_COMMANDS[0]} 0.01",
        subreddit="friendly_sub",
        parent_author="poor",
    )
    response = send_from_comment(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "status": 10,
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "username": "rich",
        "hash": "success!",
        "recipient": "poor",
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response)
        == "Sent ```0.01 Nano``` to /u/poor -- [Transaction on Nano Crawler](https"
        "://nanocrawler.cc/explorer/block/success!)"
    )

    # send by username mention
    message = RedditMessage(
        "t4_5",
        "rich",
        "",
        f"/u/{TIP_BOT_USERNAME} 0.01",
        subreddit="friendly_sub",
        parent_author="poor",
    )
    response = send_from_comment(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "status": 10,
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "username": "rich",
        "hash": "success!",
        "recipient": "poor",
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response)
        == "Sent ```0.01 Nano``` to /u/poor -- [Transaction on Nano Crawler](https"
        "://nanocrawler.cc/explorer/block/success!)"
    )

    # send at end of by username mention
    message = RedditMessage(
        "t4_5",
        "rich",
        "",
        f"something something /u/{TIP_BOT_USERNAME} 0.01",
        subreddit="friendly_sub",
        parent_author="poor",
    )
    response = send_from_comment(message)
    assert response == {
        "amount": 10000000000000000000000000000,
        "status": 10,
        "subreddit": "friendly_sub",
        "subreddit_minimum": 0.001,
        "username": "rich",
        "hash": "success!",
        "recipient": "poor",
        "subreddit_status": "full",
    }
    assert (
        text.make_response_text(message, response)
        == "Sent ```0.01 Nano``` to /u/poor -- [Transaction on Nano Crawler](https"
        "://nanocrawler.cc/explorer/block/success!)"
    )

# Test the streaming of comments and methods
class MockRedditInbox:
    i = 0
    responses = [
        ["t3_one", "t3_two"],
        ["t3_one", "t3_two", "t3_three", "t4_one"],
        ["t3_three", "t3_four", "t4_one"],
        ["t3_three", "t3_four", "t4_one"],
    ]

    def all(self, limit=25):
        response = self.responses[self.i]
        self.i += 1
        return response


class MockSubreddit:
    i = 0
    responses = [
        ["t1_one", "t1_two"],
        ["t1_one", "t1_two", "t1_three", "t4_one"],
        ["t1_three", "t1_four", "t4_one"],
        ["t1_three", "t1_four", "t4_one"],
    ]

    def comments(self):
        response = self.responses[self.i]
        self.i += 1
        return response


def test_stream_comments_messages(monkeypatch):
    reddit = types.SimpleNamespace()
    reddit.inbox = MockRedditInbox()
    monkeypatch.setattr(tipbot, "CYCLE_TIME", 0)
    monkeypatch.setattr(tipbot, "REDDIT", reddit)
    monkeypatch.setattr(tipbot, "SUBREDDITS", MockSubreddit())
    items = []
    for item in stream_comments_messages():
        items.append(item)
        if not item:
            break
    assert set(items) == {"t3_three", "t1_three", "t4_one", "t1_four", "t3_four", None}


class StoreStuff:
    """
    In short, creates a fake "function" that returns a value but stores all args and kwargs pass to it.
    It's how I test functions that don't have a return, by making sure they are invoking others with
    the correct, expected parameters.
    """

    def __init__(self, returns=None):
        self.stuff = []
        self.returns = returns

    def store(self, *args, **kwargs):
        self.stuff.append([args, kwargs])
        return self.returns


def test_return_transactions(monkeypatch):
    monkeypatch.setattr(tipper_functions, "query_sql", mock_query_sql)
    monkeypatch.setattr(tipper_functions, "exec_sql", lambda *args: None)
    pm_responses = StoreStuff()

    monkeypatch.setattr(tipper_functions, "send_pm", pm_responses.store)
    send_responses = StoreStuff({"hash": "hash"})
    monkeypatch.setattr(tipper_functions, "send", send_responses.store)
    monkeypatch.setattr(
        tipper_functions, "add_history_record", lambda *args, **kwargs: None
    )
    tipper_functions.return_transactions()
    assert send_responses.stuff == [
        [("one", "two", 500000000000000000000000000, "one"), {}],
        [
            (
                "one",
                "two",
                500000000000000000000000000,
                "nano_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij",
            ),
            {},
        ],
    ]
