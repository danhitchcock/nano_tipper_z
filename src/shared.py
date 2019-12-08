import os
import mysql.connector
import configparser
import praw
import logging
from text import COMMENT_FOOTER, HELP, WELCOME_CREATE, WELCOME_TIP, NEW_TIP


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
sql_password = config["SQL"]["sql_password"]
database_name = config["SQL"]["database_name"]
tip_bot_on = config["BOT"]["tip_bot_on"]
tip_bot_username = config["BOT"]["tip_bot_username"]
program_minimum = float(config["BOT"]["program_minimum"])
recipient_minimum = float(config["BOT"]["recipient_minimum"])
tip_commands = config["BOT"]["tip_commands"].split(",")
donate_commands = config["BOT"]["donate_commands"].split(",")
tipbot_owner = config["BOT"]["tipbot_owner"]
cmc_token = config["OTHER"]["cmc_token"]
dpow_token = config["NODE"]["dpow_token"]
default_url = config["NODE"]["default_url"]
python_command = config["BOT"]["python_command"]
tipper_options = config["BOT"]["tipper_options"]
messenger_options = config["BOT"]["messenger_options"]

# only fails if no databases have been created
try:
    mydb = mysql.connector.connect(
        user="root",
        password=sql_password,
        host="localhost",
        auth_plugin="mysql_native_password",
        database=database_name,
    )
    mycursor = mydb.cursor()
except mysql.connector.errors.DatabaseError:
    mydb = mysql.connector.connect(
        user="root",
        password=sql_password,
        host="localhost",
        auth_plugin="mysql_native_password",
    )
    mycursor = mydb.cursor()


reddit = praw.Reddit("bot1")

excluded_redditors = [
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
