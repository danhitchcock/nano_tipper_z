import shared
from shared import from_raw, NumberUtil

COMMENT_FOOTER = """\n\n
***\n\n
[*^(Banano)*](https://banano.cc)*^( | )*
[*^(Banano Tipper)*](https://github.com/BananoCoin/banano_reddit_tipbot)*^( | )*
[*^(Opt Out)*](https://reddit.com/message/compose/?to=banano_tipbot&subject=command&message=opt-out)
"""

HELP = """
Help from Banano Tipper! This bot handles tips via the [BANANO](https://banano.cc) currency.
[Visit us on GitHub](https://github.com/BananoCoin/banano_reddit_tipbot), the [Wiki](https://github.com/BananoCoin/banano_reddit_tipbot/wiki/Using-the-Banano-Reddit-TipBot) 
or /r/banano_tipbot for more information on its use and its status. Be sure to read the 
[Terms of Service](https://github.com/BananoCoin/banano_reddit_tipbot#terms-of-service)\n\n

If you do not accept the Terms of Service, or do not with to participate, please respond with the text `opt-out`.\n\n

Banano Tipper works in two ways -- either publicly tip a user on a subreddit, or send a PM to /u/banano_tipbot with a PM command below.\n\n
To tip 0.1 Banano on a comment or post on a [tracked subreddit](https://www.reddit.com/r/banano_tipbot/comments/astwp6/banano_tipbot_status/), make a comment starting with:\n
    !ban 0.1
To tip anywhere on reddit, tag the bot as such (it won't post on the all subreddits, but it will PM the users):\n
    /u/banano_tipbot 0.1
You can tip any amount above the program minimum of 0.01 Banano.\n\n

For PM commands, create a new message with any of the following commands (be sure to remove the quotes, '<'s and '>'s):\n
    'create' - Create a new account if one does not exist
    'send <amount or all> <user/address>' - Send Nano to a reddit user or an address
    'balance' or 'address' - Retrieve your account balance.
    'silence <yes/no>' - (default 'no') Prevents the bot from sending you tip notifications or tagging in posts 
    'history <optional: number of records>' - Retrieves tipbot commands. Default 10, maximum is 50.
    'opt-out' - Disables your account. 
    'opt-in' - Re-enables your account. 
    'help' - Get this help message\n
If you wanted to send 0.01 Banano to bbedward, reply:\n
    send 0.01 bbedward\n
If you have any questions or bug fixes, please reach out on the [Banano subreddit](https://reddit.com/r/banano) or the [Banano Discord](https://chat.banano.cc)."""

WELCOME_CREATE = """
Welcome to Banano Tipper, a reddit tip bot which allows you to tip and send the [BANANO](https://banano.cc) Currency to your favorite redditors! 
Your account is **active** and your Banano address is `%s`. By using this service, you agree 
to the [Terms of Service](https://github.com/BananoCoin/banano_reddit_tipbot#terms-of-service).\n\n

If you do not accept the Terms of Service, or do not with to participate, please respond with the text `opt-out`.\n\n

***\n\n
Banano Tipper can be used in two ways. The most common is to tip other redditors publicly by replying to a comment on a 
[tracked subreddit](https://www.reddit.com/r/banano_tipbot/comments/astwp6/banano_tipbot_status/). 
To tip someone 0.01 Banano, reply to their message with:\n\n
```!ban 0.01```\n\n
To tip a redditor on any subreddit, tag the bot instead of issuing a command:\n\n
```/u/banano_tipbot 0.01```\n\n
In unfamiliar subreddits, the minimum tip is 1 Banano.\n\n
***\n\n
There are also PM commands by [messaging](https://reddit.com/message/compose/?to=banano_tipbot&subject=command&message=type_command_here) /u/banano_tipbot. Remove any quotes, <'s and >'s.\n\n
```send <amount> <valid_bannano_address>``` Withdraw your Banano to your own wallet.\n\n
```send <amount> <redditor username>``` Send to another redditor.\n\n
```balance``` Check your account balance.\n\n
```help``` Receive an in-depth help message.\n\n

View your account on [the block explorer](https://creeper.banano.cc/explorer/account/%s).\n\n
If you have any questions, please post at /r/banano_tipbot
"""

WELCOME_TIP = """
Welcome to Banano Tipper, a reddit tip bot which allows you to tip and send the [BANANO](https://banano.cc) Currency to your favorite redditors! 
You have just received a Banano tip in the amount of ```%s BAN``` at your address `%s`.\n\n
By using this service, you agree to the [Terms of Service](https://github.com/BananoCoin/banano_reddit_tipbot#terms-of-service).\n\n

If you do not accept the Terms of Service, or do not with to participate, please respond with the text `opt-out`.\n\n
***\n\n
Banano Tipper can be used in two ways. The most common is to tip other redditors publicly by replying to a comment on a 
[tracked subreddit](https://www.reddit.com/r/banano_tipbot/comments/astwp6/banano_tipbot_status/). 
To tip someone 0.01 Banano, reply to their message with:\n\n
```!ban 0.01```\n\n
To tip a redditor on any subreddit, tag the bot instead of issuing a command:\n\n
```/u/banano_tipbot 0.01```\n\n
In unfamiliar subreddits, the minimum tip is 1 Banano.\n\n
***\n\n
There are also PM commands by [messaging](https://reddit.com/message/compose/?to=banano_tipbot&subject=command&message=type_command_here) /u/banano_tipbot. Remove any quotes, <'s and >'s.\n\n
```send <amount> <valid_banano_address>``` Withdraw your Banano to your own wallet.\n\n
```send <amount> <redditor username>``` Send to another redditor.\n\n
```balance``` Check your account balance.\n\n
```help``` Receive an in-depth help message.\n\n

View your account on the block explorer: https://creeper.banano.cc/explorer/account/%s\n\n
If you have any questions, please post at /r/banano_tipbot
"""

NEW_TIP = """
Somebody just tipped you %s BAN at your address `%s`. Your new account balance is:\n\n
**%s Banano**\n\n
[View this transaction on Creeper](https://creeper.banano.cc/explorer/block/%s)\n\n
To turn off these notifications, reply with "silence yes".
"""

SUBJECTS = {
    "first_tip": "Banano Tipper - Congrats on receiving your first Banano Tip!",
    "new_tip": "Banano Tipper - You just received a new Banano tip!",
    "help": "Banano Tipper - Help",
    "balance": "Banano Tipper - Account Balance",
    "minimum": "Banano Tipper - Tip Minimum",
    "create": "Banano Tipper - Create",
    "send": "Banano Tipper - Send",
    "history": "Banano Tipper - History",
    "silence": "Banano Tipper - Silence",
    "subreddit": "Banano Tipper - Subreddit",
    "opt-out": "Banano Tipper - Opt Out",
    "opt-in": "Banano Tipper - Opt In",
    "success": "Banano Tipper - Your Tip Was Successful",
    "failure": "Banano Tipper - You Tip Did Not Go Through",
    "convert": "Banano Tipper - Your Currency Conversion",
}

MINIMUM = {
    "set_min": "Updating tip minimum to %s",
    "below_program": "Did not update. The amount you specified is below the program minimum "
    "of %s Banano.",
    "parse_error": "I couldn't parse your command. I was expecting 'minimum "
    "<amount>'. Be sure to check your spacing.",
}

NAN = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."

ACCOUNT_MAKE_ERROR_ERROR = "I've experienced an error creating your account, please check with my owner or try again later."
TIP_CREATE_ACCT_ERROR = "I failed to create an account for your intended recipient, please check with my owner or try again later."

# full responses
SEND_TEXT = {
    10: (
        "Sent ```%s BAN``` to /u/%s\n\n[View this transaction on Creeper](https://creep"
        "er.banano.cc/explorer/block/%s)"
    ),
    11: (
        "Sent ```%s BAN``` to %s\n\n[View this transaction on Creeper](https://creep"
        "er.banano.cc/explorer/block/%s)"
    ),
    20: (
        "Creating a new account for /u/%s and "
        "sending ```%s BAN```.\n\n[View this transaction on Creeper](https://creeper.banano.cc"
        "/explorer/block/%s)"
    ),
    30: "Sent ```%s BAN``` to address `%s`\n\n[View this transaction on Creeper](https://creep"
    "er.banano.cc/explorer/block/%s)",
    100: (
        "You don't have an account yet. Please PM me with `create` in the body to "
        "make an account."
    ),
    110: "You must specify an amount and a user, e.g. `send 1 banano_tipbot`.",
    120: "I could not read the amount. Is '%s' a number?",
    130: "Program minimum is %s Banano.",
    150: "Your tip is below the minimum for an unfamiliar sub.",
    160: "You have insufficient funds. Please check your balance.",
    170: "'%s' is neither a redditor nor a valid address.",
    180: (
        "Sorry, the user has set a tip minimum of %s. "
        "Your tip of %s is below this amount."
    ),
    190: "Sorry, the user has opted-out of using Banano Tipper.",
    200: "You cannot send to yourself."
}

# for subreddits who like minimal response, or 2nd level responses
SEND_TEXT_MIN = {
    10: (
        "^[Sent](https://creeper.banano.cc/explorer/block/%s) ^%s ^BAN ^to ^(/u/%s) ^- "
        "[^(Banano Tipper)](https://github.com/BananoCoin/banano_reddit_tipbot)"
    ),
    11: (
        "^[Sent](https://creeper.banano.cc/explorer/block/%s) ^%s ^BAN ^to ^%s ^- [^(Bana"
        "no Tipper)](https://github.com/BananoCoin/banano_reddit_tipbot)"
    ),
    20: (
        "^(Made a new account and )^[sent](https://creeper.banano.cc/explorer/block/%s) ^%s ^BAN ^to ^(/u/%s) ^- [^(Bana"
        "no Tipper)](https://github.com/BananoCoin/banano_reddit_tipbot)"
    ),
    100: (
        "^(Tip not sent. Error code )^[%s](https://github.com/BananoCoin/banano_reddit_tipbot"
        "#error-codes) ^- [^(Banano Tipper)](https://github.com/BananoCoin/banano_reddit_tipbot)"
    ),
}

OPT_IN = """
Welcome back! You have opted back in. Your account will be restored with the same address."""

OPT_OUT = """
You have opted-out and I promise not to bother you anymore.\n\n
If this was in error, please respond with the text `opt-in`.
"""

SUBREDDIT = {
    "missing": "Your command seems to be missing something. Make sure it follow the format `subreddit <subreddit> "
    "<command> <option>.`",
    "not_mod": "You are not a moderator of /r/%s.",
    "minimum": "Sucessfully set your /r/%s minimum to %s, active immediately.",
    "deactivate": "Within 5 minutes, tipping will be deactivated in your subreddit %s.",
    "activate": "Within 5 minutes, the Banano Tipper response in your Subreddit will be set to %s.",
    "error": "There was something wrong with your activate or minimum command.",
    "all": "Here is a list of every subreddit and its status:\n\nName, Status, Minimum\n\n",
    "one": "Here are the settings for subreddit /r/%s:\n\nName, Status, Minimum\n\n",
}

SILENCE = {
    "yes_no": "I did not see 'no' or 'yes' after 'silence'. If you did type "
    "that, check your spacing.",
    "no": "Silence set to 'no'. You will receive tip notifications and be "
    "tagged by the bot in replies.",
    "yes": "Silence set to 'yes'. You will no longer receive tip "
    "notifications or be tagged by the bot.",
    "parse_error": "I couldn't parse your command. I was expecting 'silence "
    "<yes/no>'. Be sure to check your spacing.",
}

NOT_OPEN = (
    "You do not currently have an account open. To create one, "
    "respond with the text 'create' in the message body."
)

ALREADY_EXISTS = (
    "It looks like you already have an account. In any case it is now "
    "**active**. Your Banano address is `%s`."
    "\n\nhttps://creeper.banano.cc/explorer/account/%s"
)

BALANCE = (
    "Your balance at address `%s` is:\n\n"
    "**%s Banano**"
    "\n\nhttps://creeper.banano.cc/explorer/account/%s"
)


def make_response_text(message, response):

    # make a minimal response if (subreddit is tracked) AND (level 2+ or minimal)
    if ("subreddit_status" in response.keys()) and (
        response["subreddit_status"] == "minimal"
        or (str(message.parent_id)[:3] != "t3_")
    ):
        if response["status"] < 100:
            return SEND_TEXT_MIN[response["status"]] % (
                response["hash"],
                NumberUtil.format_float(from_raw(response["amount"])),
                response["recipient"],
            )
        else:
            return SEND_TEXT_MIN[100] % response["status"]

    # otherwise, it will be a full response. Even if hostile/silent (we'll send PMs)
    if response["status"] == 20:
        return SEND_TEXT[response["status"]] % (
            response["recipient"],
            NumberUtil.format_float(from_raw(response["amount"])),
            response["hash"],
        )
    if response["status"] < 100:
        return SEND_TEXT[response["status"]] % (
            NumberUtil.format_float(from_raw(response["amount"])),
            response["recipient"],
            response["hash"],
        )
    if response["status"] in [100, 110, 150, 160, 190, 200]:
        return SEND_TEXT[response["status"]]
    if response["status"] == 120:
        return SEND_TEXT[response["status"]] % response["amount"]
    if response["status"] == 130:
        return SEND_TEXT[response["status"]] % shared.PROGRAM_MINIMUM
    if response["status"] in [170, 210]:
        return SEND_TEXT[response["status"]] % response["recipient"]
    if response["status"] == 180:
        return SEND_TEXT[response["status"]] % (
            NumberUtil.format_float(from_raw(response["minimum"])),
            NumberUtil.format_float(from_raw(response["amount"])),
        )
    if response["status"] == 200:
        return SEND_TEXT[response["status"]]
    return None
