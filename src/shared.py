import os
import mysql.connector
import configparser
import praw
import logging
from text import *


LOGGER = logging.getLogger("reddit-tipbot")
LOGGER.setLevel(logging.DEBUG)
try:
    os.makedirs("log", exist_ok=True)
except:
    pass
fh = logging.FileHandler("log/info.log")
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
ch.setFormatter(formatter)
LOGGER.addHandler(fh)
LOGGER.addHandler(ch)
config = configparser.ConfigParser()
config.read("tipper.ini")
SQL_PASSWORD = config["SQL"]["sql_password"]
DATABASE_NAME = config["SQL"]["database_name"]
TIP_BOT_ON = config["BOT"]["tip_bot_on"]
TIP_BOT_USERNAME = config["BOT"]["tip_bot_username"]
PROGRAM_MINIMUM = float(config["BOT"]["program_minimum"])
RECIPIENT_MINIMUM = float(config["BOT"]["recipient_minimum"])
TIP_COMMANDS = config["BOT"]["tip_commands"].split(",")
DONATE_COMMANDS = config["BOT"]["donate_commands"].split(",")
TIPBOT_OWNER = config["BOT"]["tipbot_owner"]
CMC_TOKEN = config["OTHER"]["cmc_token"]
DPOW_TOKEN = config["NODE"]["dpow_token"]
DEFAULT_URL = config["NODE"]["default_url"]
PYTHON_COMMAND = config["BOT"]["python_command"]
TIPPER_OPTIONS = config["BOT"]["tipper_options"]
MESSENGER_OPTIONS = config["BOT"]["messenger_options"]

# only fails if no databases have been created
try:
    MYDB = mysql.connector.connect(
        user="root",
        password=SQL_PASSWORD,
        host="localhost",
        auth_plugin="mysql_native_password",
        database=DATABASE_NAME,
    )
    MYCURSOR = MYDB.cursor()
except mysql.connector.errors.DatabaseError:
    MYDB = mysql.connector.connect(
        user="root",
        password=SQL_PASSWORD,
        host="localhost",
        auth_plugin="mysql_native_password",
    )
    MYCURSOR = MYDB.cursor()


REDDIT = praw.Reddit("bot1")

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
