import datetime
import os
import configparser
import praw
import logging
import sys
import secrets
import string
import re

from bitstring import BitArray
from hashlib import blake2b

from peewee import *
from playhouse.pool  import PooledPostgresqlExtDatabase

LOGGER = logging.getLogger("banano-reddit-tipbot")
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s", "%Y-%m-%d %H:%M:%S %z")
handler.setFormatter(formatter)
LOGGER.addHandler(handler)

config = configparser.ConfigParser()
config.read(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "tipper.ini")
)

# if we have a file, use it. Otherwise, load testing defaults
try:
    TIP_BOT_ON = config["BOT"]["tip_bot_on"]
    TIP_BOT_USERNAME = config["BOT"]["tip_bot_username"]
    PROGRAM_MINIMUM = float(config["BOT"]["program_minimum"])
    RECIPIENT_MINIMUM = float(config["BOT"]["recipient_minimum"])
    TIP_COMMANDS = config["BOT"]["tip_commands"].split(",")
    TIPBOT_OWNER = config["BOT"]["tipbot_owner"]
    PYTHON_COMMAND = config["BOT"]["python_command"]
    TIPPER_OPTIONS = config["BOT"]["tipper_options"]
    MESSENGER_OPTIONS = config["BOT"]["messenger_options"]
    CURRENCY = config["BOT"]["currency"]

    DEFAULT_URL = config["NODE"]["default_url"]
    REP = config["NODE"]["rep"]
    WALLET_ID = config["NODE"]["wallet_id"]

    USE_SQLITE = config["SQL"]["use_sqlite"]
    DATABASE_HOST = config["SQL"]["database_host"]
    DATABASE_NAME = config["SQL"]["database_name"]
    DATABASE_USER = config["SQL"]["database_user"]
    DATABASE_PASSWORD = config["SQL"]["database_password"]

except KeyError as e:
    LOGGER.info("Failed to read tipper.ini. Falling back to test-defaults...")
    LOGGER.info(f"Failed on: {e}")
    SQL_PASSWORD = ""
    DATABASE_NAME = ""
    TIP_BOT_ON = True
    TIP_BOT_USERNAME = "nano_tipper_z"
    PROGRAM_MINIMUM = 0.0001
    RECIPIENT_MINIMUM = 0
    TIP_COMMANDS = ["!ntipz", "!nano_tipz"]
    TIPBOT_OWNER = "zily88"
    DEFAULT_URL = ""
    PYTHON_COMMAND = ""
    TIPPER_OPTIONS = ""
    MESSENGER_OPTIONS = ""
    CURRENCY = "Nano"
    REP = ""
    WALLET_ID = config["NODE"]["wallet_id"]
    USE_SQLITE = True

if USE_SQLITE:
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    db = SqliteDatabase(os.path.join(PROJECT_ROOT, 'tip.db'))
else:
    db = PooledPostgresqlExtDatabase(DATABASE_NAME, user=DATABASE_USER, password=DATABASE_PASSWORD, host=DATABASE_HOST, port=5432, max_connections=4)

try:
    REDDIT = praw.Reddit("bot1")
except:
    REDDIT = None

class RandomUtil(object):
    @staticmethod
    def generate_seed() -> str:
        """Generate a random seed and return it"""
        seed = "".join([secrets.choice(string.hexdigits) for i in range(64)]).upper()
        return seed

if CURRENCY == "Nano":

    def to_raw(amount):
        return round(int(amount * 10 ** 30), -20)

    def from_raw(amount):
        return amount / 10 ** 30


elif CURRENCY == "Banano":

    def to_raw(amount):
        return round(int(amount * 10 ** 24), -20)

    def from_raw(amount):
        return amount / 10 ** 24

# Base Model
class BaseModel(Model):
	class Meta:
		database = db

class History(BaseModel):
    username = CharField()
    action = CharField()
    reddit_time = DateTimeField(default=datetime.datetime.utcnow)
    sql_time = DateTimeField()
    address = CharField()
    comment_or_message = CharField()
    recipient_username = CharField()
    recipient_address = CharField()
    amount = CharField()
    hash = CharField()
    comment_id = CharField()
    comment_text = CharField()
    notes = CharField()
    return_status = CharField()

class Message(BaseModel):
    username = CharField()
    subject = CharField()
    message = TextField()

    class Meta:
        db_table = 'messages'

class Account(BaseModel):
    username = CharField(primary_key=True)
    address = CharField(unique=True)
    private_key = CharField(unique=True)
    key_released = BooleanField()
    minimum = CharField(default=to_raw(RECIPIENT_MINIMUM))
    notes = CharField()
    silence = BooleanField(default=False)
    active = BooleanField(default=False)
    opt_in = BooleanField(default=True)

    class Meta:
        db_table = 'accounts'

class Subreddit(BaseModel):
    subreddit = CharField(primary_key=True)
    reply_to_comments = BooleanField(default=True)
    footer = CharField()
    status = CharField()
    minimum = CharField()

    class Meta:
        db_table = 'subreddits'

def create_db():
	with db.connection_context():
		db.create_tables([History, Message, Account, Subreddit], safe=True)

create_db()

# initiate the bot and all friendly subreddits
def get_subreddits():
    results = Subreddit.select()
    subreddits = [subreddit for subreddit in results]
    if len(subreddits) == 0:
        return None
    subreddits_str = "+".join(result.subreddit for result in subreddits)
    return REDDIT.subreddit(subreddits_str)


# disable for testing
try:
    SUBREDDITS = get_subreddits()
except AttributeError:
    SUBREDDITS = None

class Validators():
    @classmethod
    def is_valid_address(cls, input_text: str) -> bool:
        """Return True if address is valid, false otherwise"""
        if input_text is None:
            return False
        return cls.validate_checksum_xrb(input_text)

    @staticmethod
    def is_valid_block_hash(block_hash: str) -> bool:
        if block_hash is None or len(block_hash) != 64:
            return False
        try:
            int(block_hash, 16)
        except ValueError:
            return False
        return True

    @staticmethod
    def validate_checksum_xrb(address: str) -> bool:
        """Given an xrb/nano/ban address validate the checksum"""
        if (CURRENCY == "Nano" and ((address[:5] == 'nano_' and len(address) == 65) or (address[:4] == 'xrb_' and len(address) == 64))) or (CURRENCY == "Banano" and (address[:4] == 'ban_'  and len(address) == 64)):
            # Populate 32-char account index
            account_map = "13456789abcdefghijkmnopqrstuwxyz"
            account_lookup = {}
            for i in range(0, 32):
                account_lookup[account_map[i]] = BitArray(uint=i, length=5)

            # Extract key from address (everything after prefix)
            if CURRENCY == "Nano":
                acrop_key = address[4:-8] if address[:5] != 'nano_' else address[5:-8]
            else:
                acrop_key = address[5:-8]
            # Extract checksum from address
            acrop_check = address[-8:]

            # Convert base-32 (5-bit) values to byte string by appending each 5-bit value to the bitstring, essentially bitshifting << 5 and then adding the 5-bit value.
            number_l = BitArray()
            for x in range(0, len(acrop_key)):
                number_l.append(account_lookup[acrop_key[x]])
            number_l = number_l[4:]  # reduce from 260 to 256 bit (upper 4 bits are never used as account is a uint256)

            check_l = BitArray()
            for x in range(0, len(acrop_check)):
                check_l.append(account_lookup[acrop_check[x]])
            check_l.byteswap()  # reverse byte order to match hashing format

            # verify checksum
            h = blake2b(digest_size=5)
            h.update(number_l.bytes)
            return h.hexdigest() == check_l.hex
        return False