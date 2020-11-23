import shared
from shared import from_raw

COMMENT_FOOTER = """\n\n
***\n\n
[*^(Nano)*](https://nano.org)*^( | )*
[*^(Nano Tipper)*](https://github.com/danhitchcock/nano_tipper_z)*^( | )*
[*^(Free Nano!)*](https://nanolinks.info/#faucets-free-nano)*^( | )*
[*^(Spend Nano)*](https://usenano.org/)*^( | )*
[*^(Nano Links)*](https://nanolinks.info/)*^( | )*
[*^(Opt Out)*](https://reddit.com/message/compose/?to=nano_tipper&subject=command&message=opt-out)
"""

HELP = """
Help from Nano Tipper! This bot was handles tips via the Nano currency.
[Visit us on GitHub](https://github.com/danhitchcock/nano_tipper_z), the [Wiki](http://reddit.com/r/nano_tipper/wiki/) 
or /r/nano_tipper for more information on its use and its status. Be sure to read the 
[Terms of Service](https://github.com/danhitchcock/nano_tipper_z#terms-of-service)\n\n

If you do not accept the Terms of Service, or do not with to participate, please respond with the text `opt-out`.\n\n

Nano Tipper works in two ways -- either publicly tip a user on a subreddit, or send a PM to /u/nano_tipper with a PM command below.\n\n
To tip 0.1 Nano on a comment or post on a [tracked subreddit](https://www.reddit.com/r/nano_tipper/comments/astwp6/nano_tipper_status/), make a comment starting with:\n
    !nano_tip 0.1
    -or-
    !ntip 0.1\n
To tip anywhere on reddit, tag the bot as such (it won't post on the all subreddits, but it will PM the users):\n
    /u/nano_tipper 0.1
You can tip any amount above the program minimum of 0.0001 Nano.\n\n
Also, you can specify a currency, like USD:\n
    !ntip 1USD\n

For PM commands, create a new message with any of the following commands (be sure to remove the quotes, '<'s and '>'s):\n
    'create' - Create a new account if one does not exist
    'send <amount or all> <user/address>' - Send Nano to a reddit user or an address
    'balance' or 'address' - Retrieve your account balance. Includes both pocketed and unpocketed transactions
    'minimum <amount>' - (default 0.0001) Sets a minimum amount for receiving tips
    'silence <yes/no>' - (default 'no') Prevents the bot from sending you tip notifications or tagging in posts 
    'history <optional: number of records>' - Retrieves tipbot commands. Default 10, maximum is 50.
    'percentage <percent>' - (default 10 percent) Sets a percentage of returned tips to donate to TipBot development.
    'opt-out' - Disables your account and donates your remaining Nano to the tipbot. 
    'opt-in' - Reenables your account. Your Nano may or may not still be available. 
    'help' - Get this help message\n
If you wanted to send 0.01 Nano to zily88, reply:\n
    send 0.01 zily88\n
If you have any questions or bug fixes, please contact /u/zily88."""

WELCOME_CREATE = """
Welcome to Nano Tipper, a reddit tip bot which allows you to tip and send the Nano Currency to your favorite redditors! 
Your account is **active** and your Nano address is %s. By using this service, you agree 
to the [Terms of Service](https://github.com/danhitchcock/nano_tipper_z#terms-of-service).\n\n

If you do not accept the Terms of Service, or do not with to participate, please respond with the text `opt-out`.\n\n

You will be receiving a tip of 0.001 Nano as a welcome gift! To load more Nano, try any of the the free 
[Nano Faucets](https://nanolinks.info/#faucets-free-nano), or deposit some (click on the Nanode link for a QR code), 
or receive a tip from a fellow redditor!\n\n
***\n\n
Nano Tipper can be used in two ways. The most common is to tip other redditors publicly by replying to a comment on a 
[tracked subreddit](https://www.reddit.com/r/nano_tipper/comments/astwp6/nano_tipper_status/). 
To tip someone 0.01 Nano, reply to their message with:\n\n
```!ntip 0.01```\n\n
To tip a redditor on any subreddit, tag the bot instead of issuing a command:\n\n
```/u/nano_tipper 0.01```\n\n
In unfamiliar subreddits, the minimum tip is 1 Nano.\n\n
***\n\n
There are also PM commands by [messaging](https://reddit.com/message/compose/?to=nano_tipper&subject=command&message=type_command_here) /u/nano_tipper. Remove any quotes, <'s and >'s.\n\n
```send <amount> <valid_nano_address>``` Withdraw your Nano to your own wallet.\n\n
```send <amount> <redditor username>``` Send to another redditor.\n\n
```minimum <amount>``` Prevent annoying spam by setting a receiving tip minimum.\n\n
```balance``` Check your account balance.\n\n
```help``` Receive an in-depth help message.\n\n

View your account on (the block explorer)[https://nanocrawler.cc/explorer/account/%s].\n\n
If you have any questions, please post at /r/nano_tipper
"""

WELCOME_TIP = """
Welcome to Nano Tipper, a reddit tip bot which allows you to tip and send the Nano Currency to your favorite redditors! 
You have just received a Nano tip in the amount of ```%.4g Nano``` at your address %s.\n\n
By using this service, you agree to the [Terms of Service](https://github.com/danhitchcock/nano_tipper_z#terms-of-service). Please activate your account by 
replying to this message or any tips which are 30 days old will be returned to the sender.\n\n

If you do not accept the Terms of Service, or do not with to participate, please respond with the text `opt-out`.\n\n

To load more Nano, try any of the the free 
[Nano Faucets](https://nanolinks.info/#faucets-free-nano), or deposit some (click on the Nano Crawler link for a QR code).\n\n
***\n\n
Nano Tipper can be used in two ways. The most common is to tip other redditors publicly by replying to a comment on a 
[tracked subreddit](https://www.reddit.com/r/nano_tipper/comments/astwp6/nano_tipper_status/). 
To tip someone 0.01 Nano, reply to their message with:\n\n
```!ntip 0.01```\n\n
To tip a redditor on any subreddit, tag the bot instead of issuing a command:\n\n
```/u/nano_tipper 0.01```\n\n
In unfamiliar subreddits, the minimum tip is 1 Nano.\n\n
***\n\n
There are also PM commands by [messaging](https://reddit.com/message/compose/?to=nano_tipper&subject=command&message=type_command_here) /u/nano_tipper. Remove any quotes, <'s and >'s.\n\n
```send <amount> <valid_nano_address>``` Withdraw your Nano to your own wallet.\n\n
```send <amount> <redditor username>``` Send to another redditor.\n\n
```minimum <amount>``` Prevent annoying spam by setting a receiving tip minimum.\n\n
```balance``` Check your account balance.\n\n
```help``` Receive an in-depth help message.\n\n

View your account on Nano Crawler: https://nanocrawler.cc/explorer/account/%s\n\n
If you have any questions, please post at /r/nano_tipper
"""

NEW_TIP = """
Somebody just tipped you %.4g Nano at your address %s. Your new account balance is:\n\n
Available: %s Nano\n\n
Unpocketed: %s Nano\n\n  
Unpocketed Nanos will be pocketed automatically. [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)\n\n
To turn off these notifications, reply with "silence yes".
"""

RETURN_WARNING = (
    "Somebody tipped you at least 30 days ago, but your account"
    " hasn't been activated yet.\n\nPlease activate your account by repl"
    "ying any command to this bot. If you do not, any tips 35 days or ol"
    "der will be returned.\n\n***\n\n"
)


SUBJECTS = {
    "RETURN_WARNING": "Nano Tipper - Please Activate Your Nano Tipper Account",
    "RETURN_MESSAGE": "Nano Tipper - Returned Tips",
    "first_tip": "Nano Tipper - Congrats on receiving your first Nano Tip!",
    "new_tip": "Nano Tipper - You just received a new Nano tip!",
    "help": "Nano Tipper - Help",
    "balance": "Nano Tipper - Account Balance",
    "minimum": "Nano Tipper - Tip Minimum",
    "percentage": "Nano Tipper - Returned Tip Percentage for Donation",
    "create": "Nano Tipper - Create",
    "send": "Nano Tipper - Send",
    "history": "Nano Tipper - History",
    "silence": "Nano Tipper - Silence",
    "subreddit": "Nano Tipper - Subreddit",
    "opt-out": "Nano Tipper - Opt Out",
    "opt-in": "Nano Tipper - Opt In",
    "cf_projects": "Nano Tipper - Nanocenter Projects",
    "success": "Nano Tipper - Your Tip Was Successful",
    "failure": "Nano Tipper - You Tip Did Not Go Through",
}

MINIMUM = {
    "set_min": "Updating tip minimum to %s",
    "below_program": "Did not update. The amount you specified is below the program minimum "
    "of %s Nano.",
    "parse_error": "I couldn't parse your command. I was expecting 'minimum "
    "<amount>'. Be sure to check your spacing.",
}

NAN = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."


# full responses
SEND_TEXT = {
    10: (
        "Sent ```%.4g Nano``` to /u/%s -- [Transaction on Nano Crawler](https://nanoc"
        "rawler.cc/explorer/block/%s)"
    ),
    11: (
        "Sent ```%.4g Nano``` to %s -- [Transaction on Nano Crawler](https://nanoc"
        "rawler.cc/explorer/block/%s)"
    ),
    20: (
        "Creating a new account for /u/%s and "
        "sending ```%.4g Nano```. [Transaction on Nano Crawler](https://nanocrawler.cc"
        "/explorer/block/%s)"
    ),
    30: "Sent ```%.4g Nano``` to address %s -- [Transaction on Nano Crawler](https://na"
    "nocrawler.cc/explorer/block/%s)",
    40: (
        "Donated ```%.4g Nano``` to Nanocenter Project %s -- [Transaction on Nano Craw"
        "ler](https://nanocrawler.cc/explorer/block/%s)"
    ),
    100: (
        "You don't have an account yet. Please PM me with `create` in the body to "
        "make an account."
    ),
    110: "You must specify an amount and a user, e.g. `send 1 nano_tipper`.",
    120: "I could not read the amount. Is '%s' a number?",
    130: "Program minimum is %s Nano.",
    140: (
        "It wasn't clear if you were trying to perform a currency conversion or "
        "not. If so, be sure there is no space between the amount and currency. "
        "Example: '!ntip 0.5USD'"
    ),
    150: "Your tip is below the minimum for an unfamiliar sub.",
    160: "You have insufficient funds. Please check your balance.",
    170: "'%s' is neither a redditor nor a valid address.",
    180: (
        "Sorry, the user has set a tip minimum of %s. "
        "Your tip of %s is below this amount."
    ),
    190: "Sorry, the user has opted-out of using Nano Tipper.",
    200: "Please specify a Nanocenter project, e.g. `nanocenter 1 reddit_tipbot`",
    210: "No Nanocenter project named %s was found.",
}

# for subreddits who like minimal response, or 2nd level responses
SEND_TEXT_MIN = {
    10: (
        "^[Sent](https://nanocrawler.cc/explorer/block/%s) ^%s ^Nano ^to ^(/u/%s) ^- "
        "[^(Nano Tipper)](https://github.com/danhitchcock/nano_tipper_z)"
    ),
    11: (
        "^[Sent](https://nanocrawler.cc/explorer/block/%s) ^%s ^Nano ^to ^%s ^- [^(Na"
        "no Tipper)](https://github.com/danhitchcock/nano_tipper_z)"
    ),
    20: (
        "^(Made a new account and )^[sent](https://nanocrawler.cc/explorer/block/%s) ^%s ^Nano ^to ^(/u/%s) ^- [^(Na"
        "no Tipper)](https://github.com/danhitchcock/nano_tipper_z)"
    ),
    40: (
        "^[Sent](https://nanocrawler.cc/explorer/block/%s) ^(%s Nano to NanoCenter Pro"
        "ject %s)"
    ),
    100: (
        "^(Tip not sent. Error code )^[%s](https://github.com/danhitchcock/nano_tipp"
        "er_z#error-codes) ^- [^(Nano Tipper)](https://github.com/danhitchcock/nano_"
        "tipper_z)"
    ),
}

OPT_IN = """
Welcome back! You have opted back in. Your account will be restored with the same address, 
though any Nano you had may have already been returned or donated already.
"""

OPT_OUT = """
You have opted-out and I promise not to bother you anymore.\n\n
Returnable Nano will be returned to the tippers, and the remaining balance will be donated to the tipbot fund.\n\n
If this was in error, please respond immediately with the text `opt-in`.
"""

SUBREDDIT = {
    "missing": "Your command seems to be missing something. Make sure it follow the format `subreddit <subreddit> "
    "<command> <option>.`",
    "not_mod": "You are not a moderator of /r/%s.",
    "min": "Subreddit-specific minimums aren't enabled yet. Check back soon!",
    "deactivate": "Within 5 minutes, tipping will be deactivated in your subreddit %s.",
    "activate": "Within 5 minutes, the tipbot response in your Subreddit will be set to %s.",
    "error": "There was something wrong with your activate or minimum command.",
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

RECEIVE = {
    "balance": "At address %s, you currently have %s Nano available, and %s Nano "
    "unpocketed. If you have any unpocketed, create a new "
    "message containing the word 'receive'\n\nhttps://nanocrawler.cc/explorer/account/%s",
}

NOT_OPEN = (
    "You do not currently have an account open. To create one, "
    "respond with the text 'create' in the message body."
)

ALREADY_EXISTS = (
    "It looks like you already have an account. In any case it is now "
    "**active**. Your Nano address is %s."
    "\n\nhttps://nanocrawler.cc/explorer/account/%s"
)

BALANCE = (
    "At address %s:\n\nAvailable: %s Nano\n\nUnpocketed: %s Nano\n\nNano "
    "will be pocketed automatically unless the transaction is below "
    "0.0001 Nano."
    "\n\nhttps://nanocrawler.cc/explorer/account/%s"
)

CROWD_FUNDING = {
    "projects": "Current NanoCenter Donation Projects: \n\n",
}


def make_response_text(message, response):

    # make a minimal response if (subreddit is tracked) AND (level 2+ or minimal)
    if ("subreddit_status" in response.keys()) and (
        response["subreddit_status"] == "minimal"
        or (str(message.parent_id)[:3] != "t3_")
    ):
        if response["status"] < 100:
            return SEND_TEXT_MIN[response["status"]] % (
                response["hash"],
                from_raw(response["amount"]),
                response["recipient"],
            )
        else:
            return SEND_TEXT_MIN[100] % response["status"]

    # otherwise, it will be a full response. Even if hostile/silent (we'll send PMs)
    if response["status"] == 20:
        return SEND_TEXT[response["status"]] % (
            response["recipient"],
            from_raw(response["amount"]),
            response["hash"],
        )
    if response["status"] < 100:
        return SEND_TEXT[response["status"]] % (
            from_raw(response["amount"]),
            response["recipient"],
            response["hash"],
        )
    if response["status"] in [100, 110, 140, 150, 160, 190, 200]:
        return SEND_TEXT[response["status"]]
    if response["status"] == 120:
        return SEND_TEXT[response["status"]] % response["amount"]
    if response["status"] == 130:
        return SEND_TEXT[response["status"]] % shared.PROGRAM_MINIMUM
    if response["status"] in [170, 210]:
        return SEND_TEXT[response["status"]] % response["recipient"]
    if response["status"] == 180:
        return SEND_TEXT[response["status"]] % (
            from_raw(response["minimum"]),
            from_raw(response["amount"]),
        )
    return None


PERCENTAGE = {
    "parse_error": "I couldn't parse your command. I was expecting 'percentage <amount>'. "
    "Be sure to check your spacing.",
    "neg": "Did not update. Your percentage cannot be negative.",
    "100": "Did not update. Your percentage must be 100 or lower.",
    "updating": "Updating donation percentage to %s.",
}


def make_return_message(user):
    return_message = (
        "The following tips have been returned and %s percent of each tip has been "
        "donated to the tipbot development fund:\n\n "
        "(Redditor, Total Tip Amount, Returned Amount, Donation Amount)\n\n "
    )
    message = return_message % user["percent"]
    for transaction in user["transactions"]:
        message += "%s | %s | %s | %s\n\n " % (
            transaction[0],
            transaction[1],
            transaction[2],
            transaction[3],
        )
    return message
