import datetime
import os
import configparser
import praw
import logging
import sys
import secrets
import string
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


EXCLUDED_REDDITORS = [
    "nano",
    "nanos",
    "btc",
    "xrb",
    "eth",
    "xrp",
    "eos",
    "ltc",
    "bch",
    "xlm",
    "etc",
    "neo",
    "bat",
    "aed",
    "afn",
    "all",
    "amd",
    "ang",
    "aoa",
    "ars",
    "aud",
    "awg",
    "azn",
    "bam",
    "bbd",
    "bdt",
    "bgn",
    "bhd",
    "bif",
    "bmd",
    "bnd",
    "bob",
    "bov",
    "brl",
    "bsd",
    "btn",
    "bwp",
    "byr",
    "bzd",
    "cad",
    "cdf",
    "che",
    "chf",
    "chw",
    "clf",
    "clp",
    "cny",
    "cop",
    "cou",
    "crc",
    "cuc",
    "cup",
    "cve",
    "czk",
    "djf",
    "dkk",
    "dop",
    "dzd",
    "egp",
    "ern",
    "etb",
    "eur",
    "fjd",
    "fkp",
    "gbp",
    "gel",
    "ghs",
    "gip",
    "gmd",
    "gnf",
    "gtq",
    "gyd",
    "hkd",
    "hnl",
    "hrk",
    "htg",
    "huf",
    "idr",
    "ils",
    "inr",
    "iqd",
    "irr",
    "isk",
    "jmd",
    "jod",
    "jpy",
    "kes",
    "kgs",
    "khr",
    "kmf",
    "kpw",
    "krw",
    "kwd",
    "kyd",
    "kzt",
    "lak",
    "lbp",
    "lkr",
    "lrd",
    "lsl",
    "lyd",
    "mad",
    "mdl",
    "mga",
    "mkd",
    "mmk",
    "mnt",
    "mop",
    "mru",
    "mur",
    "mvr",
    "mwk",
    "mxn",
    "mxv",
    "myr",
    "mzn",
    "nad",
    "ngn",
    "nio",
    "nok",
    "npr",
    "nzd",
    "omr",
    "pab",
    "pen",
    "pgk",
    "php",
    "pkr",
    "pln",
    "pyg",
    "qar",
    "ron",
    "rsd",
    "rub",
    "rwf",
    "sar",
    "sbd",
    "scr",
    "sdg",
    "sek",
    "sgd",
    "shp",
    "sll",
    "sos",
    "srd",
    "ssp",
    "stn",
    "svc",
    "syp",
    "szl",
    "thb",
    "tjs",
    "tmt",
    "tnd",
    "top",
    "try",
    "ttd",
    "twd",
    "tzs",
    "uah",
    "ugx",
    "usd",
    "usn",
    "uyi",
    "uyu",
    "uzs",
    "vef",
    "vnd",
    "vuv",
    "wst",
    "xaf",
    "xcd",
    "xdr",
    "xof",
    "xpf",
    "xsu",
    "xua",
    "yer",
    "zar",
    "zmw",
    "zwl",
]

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
    if results.count() == 0:
        return None
    subreddits = "+".join(result.subreddit for result in results)
    return REDDIT.subreddit(subreddits)


# disable for testing
try:
    SUBREDDITS = get_subreddits()
except AttributeError:
    SUBREDDITS = None