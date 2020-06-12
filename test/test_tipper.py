import time
import tipbot
import tipper_functions
from shared import TIP_COMMANDS, TIP_BOT_USERNAME
import pytest


class RedditMessage:
    def __init__(
        self,
        name="",
        author="",
        subject="",
        body="",
        created_utc=time.time(),
        subreddit="nano_tipper_z",
    ):
        self.name = name
        self.author = author
        self.body = body
        self.subject = subject
        self.created_utc = created_utc
        self.subreddit = subreddit


@pytest.fixture()
def mock_stuff(monkeypatch):
    monkeypatch.setattr()


"""

def test_send_nano(monkeypatch):
    
    def mock_history_record(*args, **kwargs):
        return 0

    def mock_mycursor_execute(*args, **kwargs):
        if True:
            return None
        else:
            return None

    def mock_commit(*args, **kwargs):
        return None


    # monkeypatch.setattr('add_history_record', mock_history_record)
    # monkeypatch.setattr(mycursor, 'add_history_record', mock_history_record)
    # monkeypatch.setattr('add_history_record', mock_history_record)



def mock_commit(*args, **kwargs):
    return "success"


def test_test_function(monkeypatch):
    monkeypatch.setattr(mydb, "commit", mock_commit)

"""


def test_parse_action():
    tests = [
        ("comment", RedditMessage("t1_1", "daniel", "", f"{TIP_COMMANDS[0]} .1"),),
        (
            "comment",
            RedditMessage("t1_2", "daniel", "", f"great job {TIP_COMMANDS[0]} .1"),
        ),
        (
            "username_mention",
            RedditMessage("t4_3", "daniel", "", f"/u/{TIP_BOT_USERNAME} .1"),
        ),
        (
            "username_mention",
            RedditMessage("t4_4", "daniel", "", f"nice /u/{TIP_BOT_USERNAME} .1"),
        ),
        ("message", RedditMessage("t4_5", "daniel", "", "history"),),
        (
            "faucet_tip",
            RedditMessage("t4_6", "nano_tipper_z", "", "send 0.001 someone"),
        ),
    ]

    for test in tests:
        assert test[0] == tipbot.parse_action(test[1])


def test_graceful_list():
    a = tipper_functions.GracefulList([1, 2, 3, 4])
    assert a[4] is None
    assert (a + [4])[5] is None
