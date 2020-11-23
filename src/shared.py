import os
import mysql.connector
import configparser
import praw
import logging


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

# if we have a file, use it. Otherwise, load testing defaults
try:
    SQL_PASSWORD = config["SQL"]["sql_password"]
    DATABASE_NAME = config["SQL"]["database_name"]
    TIP_BOT_ON = config["BOT"]["tip_bot_on"]
    TIP_BOT_USERNAME = config["BOT"]["tip_bot_username"]
    PROGRAM_MINIMUM = float(config["BOT"]["program_minimum"])
    RECIPIENT_MINIMUM = float(config["BOT"]["recipient_minimum"])
    TIP_COMMANDS = config["BOT"]["tip_commands"].split(",")
    DONATE_COMMANDS = config["BOT"]["donate_commands"].split(",")
    TIPBOT_OWNER = config["BOT"]["tipbot_owner"]
    TIPBOT_DONATION_ADDRESS = config["BOT"]["tipbot_donation_address"]
    CMC_TOKEN = config["OTHER"]["cmc_token"]
    DPOW_TOKEN = config["NODE"]["dpow_token"]
    DPOW_USERNAME = config["NODE"]["dpow_username"]
    DEFAULT_URL = config["NODE"]["default_url"]
    PYTHON_COMMAND = config["BOT"]["python_command"]
    TIPPER_OPTIONS = config["BOT"]["tipper_options"]
    MESSENGER_OPTIONS = config["BOT"]["messenger_options"]
    DONATION_ADMINS = config["BOT"]["donation_admins"]
    CURRENCY = config["bot"]["currency"]
    REP = config["bot"]["rep"]
except KeyError as e:
    LOGGER.info("Failed to read tipper.ini. Falling back to test defaults...")
    LOGGER.info(e)
    SQL_PASSWORD = ""
    DATABASE_NAME = ""
    TIP_BOT_ON = True
    TIP_BOT_USERNAME = "nano_tipper_z"
    PROGRAM_MINIMUM = 0.0001
    RECIPIENT_MINIMUM = 0
    TIP_COMMANDS = ["!ntipz", "!nano_tipz"]
    DONATE_COMMANDS = ["!nanocenterz"]
    TIPBOT_OWNER = "zily88"
    TIPBOT_DONATION_ADDRESS = (
        "nano_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij"
    )
    CMC_TOKEN = ""
    DPOW_TOKEN = ""
    DPOW_USERNAME = ""
    DEFAULT_URL = ""
    PYTHON_COMMAND = ""
    TIPPER_OPTIONS = ""
    MESSENGER_OPTIONS = ""
    DONATION_ADMINS = []
    CURRENCY = "Nano"
    REP = ""

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
    try:
        MYDB = mysql.connector.connect(
            user="root",
            password=SQL_PASSWORD,
            host="localhost",
            auth_plugin="mysql_native_password",
        )
        MYCURSOR = MYDB.cursor()
    except mysql.connector.errors.DatabaseError:
        MYDB = None
        MYCURSOR = None

try:
    REDDIT = praw.Reddit("bot1")
except:
    REDDIT = None


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


# initiate the bot and all friendly subreddits
def get_subreddits():
    MYCURSOR.execute("SELECT subreddit FROM subreddits")
    results = MYCURSOR.fetchall()
    MYDB.commit()
    if len(results) == 0:
        return None
    subreddits = "+".join(result[0] for result in results)
    return REDDIT.subreddit(subreddits)


# disable for testing
try:
    SUBREDDITS = get_subreddits()
except AttributeError:
    SUBREDDITS = None


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
