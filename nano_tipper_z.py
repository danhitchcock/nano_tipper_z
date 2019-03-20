import praw
import time
from datetime import datetime
from time import sleep
from rpc_bindings import open_account, generate_account, generate_qr, nano_to_raw, receive_all, send_all, \
    check_balance, validate_address, open_or_receive, get_pendings, open_or_receive_blocks
from rpc_bindings import send_w as send
import mysql.connector
import configparser

# access the sql library
config = configparser.ConfigParser()
config.read('./tipper.ini')
config.sections()
sql_password = config['SQL']['sql_password']
database_name = config['SQL']['database_name']
tip_bot_on = config['BOT']['tip_bot_on']
tip_bot_username = config['BOT']['tip_bot_username']
program_minimum = float(config['BOT']['program_minimum'])
recipient_minimum = float(config['BOT']['recipient_minimum'])
tip_commands = config['BOT']['tip_commands'].split(',')

mydb = mysql.connector.connect(user='root', password=sql_password,
                              host='localhost',
                              auth_plugin='mysql_native_password', database=database_name)
mycursor = mydb.cursor()

# initiate the bot and all friendly subreddits
reddit = praw.Reddit('bot1')

mycursor.execute("SELECT subreddit FROM subreddits")
results = mycursor.fetchall()
subreddits=''
for result in results:
    subreddits += '%s+' % result[0]

subreddits = subreddits[:-1]
print('Initializng in: ', subreddits)
subreddit = reddit.subreddit(subreddits)

# a few globals
program_maximum = 10
excluded_reditors = ['nano', 'nanos', 'xrb', 'usd', 'eur', 'btc', 'yen']
toggle_receive = True
print(repr(tip_bot_username))


comment_footer = """\n\n
***\n\n
[*^(Nano)*](https://nano.org)*^( | )*
[*^(Nano Tipper)*](https://github.com/danhitchcock/nano_tipper_z)*^( | )*
[*^(Free Nano!)*](https://nanolinks.info/#faucets-free-nano)*^( | )*
[*^(Spend Nano)*](https://usenano.org/)*^( | )*
[*^(Nano Links)*](https://nanolinks.info/)"""

help_text = """
Help from Nano Tipper! This bot was handles tips via the Nano cryptocurrency.
[Visit us on GitHub](https://github.com/danhitchcock/nano_tipper_z), the [Wiki](http://reddit.com/r/nano_tipper/wiki/) 
or /r/nano_tipper for more information on its use and its status. Be sure to read the 
[Terms of Service](https://github.com/danhitchcock/nano_tipper_z#terms-of-service)\n\n

Nano Tipper works in two ways -- either publicly tip a user on a subreddit, or send a PM to /u/nano_tipper with a PM command below.\n\n
To tip 0.1 Nano on a comment or post on a [tracked subreddit](https://www.reddit.com/r/nano_tipper/comments/astwp6/nano_tipper_status/), make a comment starting with:\n
    !nano_tip 0.1
    -or-
    !ntip 0.1\n
To tip anywhere on reddit, tag the bot as such (it won't post on the all subreddits, but it will PM the users):\n
    /u/nano_tipper 0.1
You can tip any amount above the program minimum of 0.0001 Nano.\n\n
    
For PM commands, create a new message with any of the following commands (be sure to remove the quotes, '<'s and '>'s):\n
    'create' - Create a new account if one does not exist
    'send <amount or all> <user/address>' - Send Nano to a reddit user or an address
    'receive' - Receive all pending transactions (if autoreceive is set to 'no')
    'balance' or 'address' - Retrieve your account balance. Includes both pocketed and unpocketed transactions
    'minimum <amount>' - (default 0.0001) Sets a minimum amount for receiving tips
    'auto_receive <yes/no>' - (default 'yes') Automatically pockets transactions. Checks every 12 seconds
    'silence <yes/no>' - (default 'no') Prevents the bot from sending you tip notifications or tagging in posts 
    'history <optional: number of records>' - Retrieves tipbot commands. Default 10, maximum is 50.
    'private_key' - (disabled) Retrieve your account private key
    'new_address' - (disabled) If you feel this address was compromised, create a new account and key
    'help' - Get this help message\n
If you wanted to send 0.01 Nano to zily88, reply:\n
    send 0.01 zily88\n
If you have any questions or bug fixes, please contact /u/zily88."""

welcome_create = """
Welcome to Nano Tipper, a reddit tip bot which allows you to tip and send the Nano Currency to your favorite redditors! 
Your account is **active** and your Nano address is %s. By using this service, you agree 
to the [Terms of Service](https://github.com/danhitchcock/nano_tipper_z#terms-of-service).\n\n

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

welcome_tipped = """
Welcome to Nano Tipper, a reddit tip bot which allows you to tip and send the Nano Currency to your favorite redditors! 
You have just received a Nano tip in the amount of ```%s Nano``` at your address %s.\n\n
By using this service, you agree to the [Terms of Service](https://github.com/danhitchcock/nano_tipper_z#terms-of-service). Please activate your account by 
replying to this message or any tips which are 30 days old will be returned to the sender.\n\n
To load more Nano, try any of the the free 
[Nano Faucets](https://nanolinks.info/#faucets-free-nano), or deposit some (click on the Nano Crawler link for a QR code).\n\n
***\n\n
Nano Tipper can be used in two ways. The most common is to tip other redditors publicly by replying to a comment on a 
[tracked subreddit](https://www.reddit.com/r/nano_tipper/comments/astwp6/nano_tipper_status/). 
To tip someone 0.01 Nano, reply to their message with:\n\n
```!ntip 0.01```\n\n
To tip a redditor on any subreddit, tag the bot instead of issuing a command:\n\n
```/u/nano_tipper 0.01```\n\n
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

new_tip = """
Somebody just tipped you %s Nano at your address %s. Your new account balance will be %s received and %s unpocketed. 
If autoreceive is on, this will be pocketed automatically. [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)\n\n
To turn off these notifications, reply with "silence yes".
"""

# generator to stream comments and messages to the main loop at the bottom, and contains the auto_receive functionality.
# Maybe this wasn't necessary, but I never get to use generators.
# To check for new messages and comments, the function scans the subreddits and inbox every 6 seconds and builds a
# set of current message. I compare the old set with the new set.
def stream_comments_messages():
    previous_comments = {comment for comment in subreddit.comments()}
    previous_messages = {message for message in reddit.inbox.all(limit=25)}
    print('Received first stream!')
    global toggle_receive
    while True:
        if toggle_receive and tip_bot_on:
            auto_receive()
        toggle_receive = not toggle_receive

        sleep(6)

        updated_comments = {comment for comment in subreddit.comments()}
        new_comments = updated_comments - previous_comments
        previous_comments = updated_comments

        # check for new messages
        updated_messages = {message for message in reddit.inbox.all(limit=25)}
        new_messages = updated_messages - previous_messages
        previous_messages = updated_messages

        # send anything new to our main program
        # also, check the message type. this will prevent posts from being seen as messages
        if len(new_comments) >= 1:

            for new_comment in new_comments:
                #print(new_comment.name)
                # if new_comment starts with 't1_'
                if new_comment.name[:3] == 't1_':
                    yield ('comment', new_comment)
        if len(new_messages) >= 1:
            for new_message in new_messages:
                # print(new_message, new_message.subject, new_message.body)
                if new_message.name[:3] == 't4_':
                    yield ('message', new_message)
                elif (new_message.subject == "comment reply" or new_message.subject == "username mention" or new_message.subject == "post reply") and new_message.name[:3] == 't1_':
                    # print('****username mention + comment reply')
                    yield ('username mention', new_message)
        else:
            yield None


#I don't know what this was for
def update_history():
    return None


# a few helper functions
def activate(author):
    sql = "UPDATE accounts SET active = TRUE WHERE username = %s"
    val = (str(author),)
    mycursor.execute(sql, val)
    mydb.commit()


def add_new_account(username):
    address = generate_account()
    private = address['private']
    address = address['account']
    sql = "INSERT INTO accounts (username, private_key, address, minimum, auto_receive, silence, active) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    val = (username, private, address, nano_to_raw(recipient_minimum), True, False, False)
    mycursor.execute(sql, val)
    mydb.commit()
    return address


def add_history_record(username=None, action=None, sql_time=None, address=None, comment_or_message=None,
                       recipient_username=None, recipient_address=None, amount=None, hash=None, comment_id=None,
                       notes=None, reddit_time=None, comment_text=None):
    if sql_time is None:
        sql_time = time.strftime('%Y-%m-%d %H:%M:%S')

    sql = "INSERT INTO history (username, action, sql_time, address, comment_or_message, recipient_username, " \
          "recipient_address, amount, hash, comment_id, notes, reddit_time, comment_text) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

    val = (username, action, sql_time, address, comment_or_message, recipient_username, recipient_address, amount,
           hash, comment_id, notes, reddit_time, comment_text)

    mycursor.execute(sql, val)
    mydb.commit()
    return mycursor.lastrowid


def allowed_request(username, seconds=30, num_requests=5):
    """ Spam prevention
    :param username: str (username)
    :param seconds: int (time period to allow the num_requests)
    :param num_requests: int (number of allowed requests)
    :return:
    """
    sql = 'SELECT sql_time FROM history WHERE username=%s'
    val = (str(username), )
    mycursor.execute(sql, val)
    myresults = mycursor.fetchall()
    if len(myresults) < num_requests:
        return True
    else:
        return (datetime.fromtimestamp(time.time()) - myresults[-5][0]).total_seconds() > seconds


def check_registered_by_address(address):
    address = address.split('_')[1]

    sql = "SELECT username FROM accounts WHERE address=%s"
    val = ('xrb_' + address, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result) > 0:
        return result[0][0]

    sql = "SELECT username FROM accounts WHERE address=%s"
    val = ('nano_' + address, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result) > 0:
        return result[0][0]

    return None


def get_user_settings(recipient_username, recipient_address=''):
    """

    :param recipient_username: str
    :param recipient_address: str
    :return: 3 items to unpack - int, str, bool
    """
    user_minimum = -1
    silence = False
    if recipient_username:
        sql = "SELECT minimum, address, silence FROM accounts WHERE username = %s"
        val = (recipient_username,)
        mycursor.execute(sql, val)
        myresult = mycursor.fetchall()
        if len(myresult) > 0:
            user_minimum = int(myresult[0][0])
            silence = myresult[0][2]
            if not recipient_address:
                recipient_address = myresult[0][1]
    return user_minimum, recipient_address, silence


# actually sends the nano -- called by "handle_send" and "handle_comment"
def handle_send_nano(message, parsed_text, comment_or_message):
    """
    parses tip amount and users from a reddit !nano_tip or PM Send command and performs the transaction. Returns a list
    with status information
    :param message: reddit comment or message object
    :param parsed_text: list
    :param comment_or_message: str
    :return: list [str, int, float, str, str, str]
    """
    # the parsed list is the first line comment body in lowercase with slashes removed and split at spaces
    # i.e. parsed_text = str(message.body).lower().replace('\\', '').split('\n')[0].split(' ')
    # for example -- ['!nano_tip', '0.1', 'zily88']
    # handle_send_nano will return a list
    # [message, status_code, tip_amount, recipient_username, recipient_address, hash]

    # set the account to activate it if it was a new one
    activate(message.author)

    # declare a few variables so I can keep track of them. They will be redeclared later
    username = str(message.author)  # the sender
    private_key = ''  # the sender's private key
    user_or_address = ''  # either 'user' or 'address', depending on how the recipient was specified
    recipient = ''  # could be an address or redditor. Will be renamed recipient_username or recipient_address below
    recipient_username = ''  # the recipient username, should one exist
    recipient_address = ''  # the recipient nano address
    message_time = datetime.utcfromtimestamp(message.created_utc) # time the reddit message was created

    # update our history database with a record. we'll modify this later depending on the outcome of the tip
    entry_id = add_history_record(
        username=username,
        action='send',
        comment_or_message=comment_or_message,
        comment_id=message.name,
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
        comment_text=str(message.body)[:255]
        )

    # check if the message body was parsed into 2 or 3 words. If it wasn't, update the history db
    # with a failure and return the message. If the length is 2 (meaning recipient is parent message author) we will
    # check that after tip amounts to limit API requests
    if len(parsed_text) >= 3:
        recipient = parsed_text[2]
    elif len(parsed_text) == 2:
        # parse the user info in a later block of code to minimize API requests
        pass
    else:
        sql = "UPDATE history SET notes = %s WHERE id = %s"
        val = ('could not find tip amount', entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        response ='Could not read your tip command.'
        return [response, 0, None, None, None, None]

    # check that the tip is a number or 'all'
    # if the amount is 'all', we need to lookup the users account balance
    if parsed_text[1].lower() == 'nan' or ('inf' in parsed_text[1].lower()):
        sql = "UPDATE history SET notes = %s WHERE id = %s"
        val = ('could not parse amount', entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        response = "Could not read your tip or send amount. Is '%s' a number?" % parsed_text[1]
        return [response, 1, None, None, None, None]
    elif parsed_text[1].lower() == 'all':
        sql = "SELECT address FROM accounts WHERE username = %s"
        val = (username,)
        mycursor.execute(sql, val)
        result = mycursor.fetchall()
        if len(result) > 0:
            address = result[0][0]
            balance = check_balance(address)
            amount = balance[0]
        else:
            response = 'You do not have a tip bot account yet. PM me "create".'
            return [response, 2, None, None, None, None]
    else:
        try:
            amount = nano_to_raw(float(parsed_text[1]))
        except:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ('could not parse amount', entry_id)
            mycursor.execute(sql, val)
            mydb.commit()
            response = "Could not read your tip or send amount. Is '%s' a number?" % parsed_text[1]
            return [response, 1, None, None, None, None]

    if amount < nano_to_raw(program_minimum):
        sql = "UPDATE history SET notes = %s WHERE id = %s"
        val = ('amount below program limit', entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        response = 'Program minimum is %s Nano.' % program_minimum
        return [response, 3, amount / 10**30, None, None, None]

    # check if author has an account, and if they have enough funds
    sql = "SELECT address, private_key FROM accounts WHERE username=%s"
    val = (username, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result) < 1:
        sql = "UPDATE history SET notes = %s WHERE id = %s"
        val = ('sender does not have an account', entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        response = 'You do not have a tip bot account yet. PM me "create".'
        return [response, 2, amount / 10 ** 30, None, None, None]
    else:
        address = result[0][0]
        private_key = result[0][1]
        results = check_balance(result[0][0])
        if amount > results[0]:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ('insufficient funds', entry_id)
            mycursor.execute(sql, val)
            mydb.commit()
            response = 'You have insufficient funds (%s Nano)'%(results[0]/10**30)
            return [response, 4, amount / 10 ** 30, None, None, None]

    # if the command was from a PM, extract the recipient username or address
    # otherwise it was a comment, and extract the parent author
    if comment_or_message == 'message':
        if len(parsed_text) == 2:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ("no recipient specified", entry_id)
            mycursor.execute(sql, val)
            mydb.commit()
            response = "You must specify an amount and a user."
            return [response, 5, amount / 10 ** 30, None, None, None]
        # remove the /u/ or u/
        if recipient[:3].lower() == '/u/':
            recipient = recipient[3:]
        elif recipient[:2].lower() == 'u/':
            recipient = recipient[2:]
        # recipient -- first check if it is a valid address. Otherwise, check if it's a redditor
        if (recipient[:5].lower() == "nano_") or (recipient[:4].lower() == "xrb_"):
            # check valid address
            success = validate_address(recipient)
            if success['valid'] == '1':
                user_or_address = 'address'
            # if not, check if it is a redditor disguised as an address (e.g. nano_is_awesome, nano_tipper_z)
            else:
                try:
                    dummy = getattr(reddit.redditor(recipient), 'is_suspended', False)
                    user_or_address = 'user'
                except:
                    # not a valid address or a redditor
                    sql = "UPDATE history SET notes = %s WHERE id = %s"
                    val = ('invalid address or address-like redditor does not exist', entry_id)
                    mycursor.execute(sql, val)
                    mydb.commit()

                    response = '%s is neither a valid address nor a redditor' % recipient
                    return [response, 6, amount / 10 ** 30, None, None, None]
        else:
            # a username was specified
            try:
                dummy = getattr(reddit.redditor(recipient), 'is_suspended', False)
                user_or_address = 'user'
            except:
                sql = "UPDATE history SET notes = %s WHERE id = %s"
                val = ('redditor does not exist', entry_id)
                mycursor.execute(sql, val)
                mydb.commit()
                response = "Could not find redditor %s. Make sure you aren't writing or copy/pasting markdown." % recipient
                return [response, 7, amount / 10 ** 30, None, None, None]
    else:
        recipient = str(message.parent().author)
        user_or_address = 'user'

    # at this point:
    # 'amount' is a valid positive number in raw and above the program minimum
    # the sender, 'username', has a valid account and enough Nano for the tip
    # how the recipient was specified, 'user_or_address', is either 'user' or 'address',
    # 'recipient' is either a valid redditor or a valid Nano address. We need to figure out which


    # if a user is specified, reassign that as the username
    # otherwise check if the address is registered
    if user_or_address == 'user':
        recipient_username = recipient
    else:
        recipient_address = recipient
        recipient_username = check_registered_by_address(recipient_address)


    # if there is a recipient_username, check their minimum
    # also pull the address
    user_minimum, recipient_address, silence = get_user_settings(recipient_username, recipient_address)

    # if either we had an account or address which has been registered, recipient_address and recipient_username will
    # have values instead of being ''. We will check the minimum
    # Three things could happen, and are parsed by this if statement
    # if the redditor is in the database,
    #   send Nano to the redditor
    # elif it's just an address that's not registered
    #   send to the address
    # else
    #   create a new address for the redditor and send
    if recipient_username in excluded_reditors:
        response = "Sorry, the redditor '%s' is in the list of exluded addresses. More than likely you didn't intend to send to that user." % (recipient_username)
        return [response, 0, amount / 10 ** 30, recipient_username, recipient_address, None]

    if (user_minimum >= 0) and recipient_address and recipient_username:
        if amount < user_minimum:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ("below user minimum", entry_id)
            mycursor.execute(sql, val)
            mydb.commit()
            response = "Sorry, the user has set a tip minimum of %s. " \
                   "Your tip of %s is below this amount." % (user_minimum/10**30, amount/10**30)
            return [response, 8, amount / 10 ** 30, recipient_username, recipient_address, None]


        if user_or_address == 'user':
            notes = "sent to registered redditor"
        else:
            notes = "sent to registered address"

        receiving_new_balance = check_balance(recipient_address)
        sql = "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, " \
              "recipient_address = %s, amount = %s WHERE id = %s"
        val = (notes, address, username, recipient_username, recipient_address, str(amount), entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        print("Sending Nano: ", address, private_key, amount, recipient_address, recipient_username)
        t0 = time.time()
        sent = send(address, private_key, amount, recipient_address)
        # print(time.time()-t0)
        sql = "UPDATE history SET hash = %s, return_status = 'cleared' WHERE id = %s"
        val = (sent['hash'], entry_id)
        mycursor.execute(sql, val)
        mydb.commit()

        if comment_or_message == "message" and (not silence):
            message_recipient = str(recipient_username)
            subject = 'You just received a new Nano tip!'

            message_text = new_tip % (
                        amount / 10 ** 30, recipient_address, receiving_new_balance[0] / 10 ** 30,
                        (receiving_new_balance[1] / 10 ** 30 + amount / 10 ** 30), sent['hash']) + comment_footer
            # reddit.redditor(message_recipient).message(subject, message_text)
            sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
            val = (message_recipient, subject, message_text)
            mycursor.execute(sql, val)
            mydb.commit()


        if user_or_address == 'user':
            if silence:
                response = "Sent ```%s Nano``` to %s -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (
                       amount / 10 ** 30, recipient_username, sent['hash'])
                return [response, 9, amount / 10 ** 30, recipient_username, recipient_address, sent['hash']]
            else:
                response = "Sent ```%s Nano``` to /u/%s -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (
                       amount / 10 ** 30, recipient_username, sent['hash'])
                return [response, 10, amount / 10 ** 30, recipient_username, recipient_address, sent['hash']]
        else:
            response = "Sent ```%s Nano``` to [%s](https://nanocrawler.cc/explorer/account/%s) -- " \
                   "[Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (
                   amount / 10 ** 30, recipient_address, recipient_address, sent['hash'])
            return [response, 11, amount / 10 ** 30, recipient_username, recipient_address, sent['hash']]

    elif recipient_address:
        # or if we have an address but no account, just send
        sql = "UPDATE history SET notes = %s, address = %s, username = %s, recipient_address = %s, amount = %s WHERE id = %s"
        val = (
            'sent to unregistered address', address, username, recipient_address, str(amount), entry_id)
        mycursor.execute(sql, val)
        mydb.commit()

        print("Sending Unregistered Address: ", address, private_key, amount, recipient_address)
        sent = send(address, private_key, amount, recipient_address)
        sql = "UPDATE history SET hash = %s, return_status = 'cleared' WHERE id = %s"
        val = (sent['hash'], entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        response =  "Sent ```%s Nano``` to [%s](https://nanocrawler.cc/explorer/account/%s). -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (amount/ 10 ** 30, recipient_address, recipient_address, sent['hash'])
        return [response, 12, amount / 10 ** 30, recipient_username, recipient_address, sent['hash']]

    else:
        # create a new account for redditor
        recipient_address = add_new_account(recipient_username)
        message_recipient = str(recipient_username)
        subject = 'Congrats on receiving your first Nano Tip!'
        message_text = welcome_tipped % (amount/ 10 ** 30, recipient_address, recipient_address) + comment_footer

        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (message_recipient, subject, message_text)
        mycursor.execute(sql, val)
        mydb.commit()
        # x = reddit.redditor(message_recipient).message(subject, message_text)


        sql = "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, recipient_address = %s, amount = %s WHERE id = %s"
        val = ("new user created", address, username, recipient_username, recipient_address,
               str(amount), entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        sent = send(address, private_key, amount, recipient_address)
        sql = "UPDATE history SET hash = %s, return_status = 'cleared' WHERE id = %s"
        val = (sent['hash'], entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        print("Sending New Account Address: ", address, private_key, amount, recipient_address, recipient_username)
        response = "Creating a new account for /u/%s and "\
                      "sending ```%s Nano```. [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (recipient_username, amount / 10 **30, sent['hash'])
        return [response, 13, amount / 10 ** 30, recipient_username, recipient_address, sent['hash']]


# handles tip commands on subreddits
def handle_comment(message, parsed_text=None):
    """
    Prepares a reddit comment starting with !nano_tip to send nano if everything goes well
    :param message:
    :param parsed_text
    :return:
    """
    # remove an annoying extra space that might be in the front

    # for prop in dir(message):
    #     print(prop)
    if parsed_text is None:
        if message.body[0] == ' ':
            parsed_text = str(message.body[1:]).lower().replace('\\', '').split('\n')[0].split(' ')
        else:
            parsed_text = str(message.body).lower().replace('\\', '').split('\n')[0].split(' ')
    response = handle_send_nano(message, parsed_text, 'comment')

    # apply the subreddit rules to our response message
    # potential statuses:
    #   friendly
    #   hostile
    #   minimal
    # if it is a friendly subreddit, just reply with the response + comment_footer
    # if it is not friendly, we need to notify the sender as well as the recipient if they have not elected silence
    # handle top level comment
    sql = 'SELECT status FROM subreddits WHERE subreddit=%s'
    val = (str(message.subreddit).lower(), )
    mycursor.execute(sql, val)
    results = mycursor.fetchall()


    if len(results) == 0:
        subreddit_status = 'hostile'

    else:
        subreddit_status = results[0][0]
    # if it is a top level reply and the subreddit is friendly
    if (str(message.parent_id)[:3] == 't3_') and (subreddit_status == 'friendly'):
        message.reply(response[0] + comment_footer)
    # otherwise, if the subreddit is friendly (and reply is not top level) or subreddit is minimal
    elif (subreddit_status == 'friendly') or (subreddit_status == 'minimal'):
        if response[1] <= 8:
            message.reply('^(Tip not sent. Error code )^[%s](https://github.com/danhitchcock/nano_tipper_z#error-codes) ^- [^(Nano Tipper)](https://github.com/danhitchcock/nano_tipper_z)'
                          % response[1])
        elif (response[1] == 9):
            message.reply('^[Sent](https://nanocrawler.cc/explorer/block/%s) ^%s ^Nano ^to ^%s ^- [^(Nano Tipper)](https://github.com/danhitchcock/nano_tipper_z)'
                          % (response[5], response[2], response[3]))
        elif (response[1] == 10) or (response[1] == 13):
            # user didn't request silence or it's a new account, so tag them
            message.reply(
                '^[Sent](https://nanocrawler.cc/explorer/block/%s) ^%s ^Nano ^to ^(/u/%s) ^- [^(Nano Tipper)](https://github.com/danhitchcock/nano_tipper_z)'
                % (response[5], response[2], response[3]))
        elif (response[1] == 11) or (response[1] == 12):
            # this actually shouldn't ever happen
            message.reply(
                '^[Sent](https://nanocrawler.cc/explorer/block/%s) ^(%s Nano to %s)' % (response[5], response[2], response[4]))
    elif subreddit_status == 'hostile':
        # it's a hostile place, no posts allowed. Will need to PM users
        if response[1] <= 8:
            message_recipient = str(message.author)
            subject = 'Your Nano tip did not go through'
            message_text = response[0] + comment_footer
            sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
            val = (message_recipient, subject, message_text)
            mycursor.execute(sql, val)
            mydb.commit()
            # reddit.redditor(str(message.author)).message('Your Nano tip did not go through', response[0] + comment_footer)
        else:
            # if it was a new account, a PM was already sent to the recipient
            message_recipient = str(message.author)
            subject = 'Successful tip!'
            message_text = response[0] + comment_footer
            sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
            val = (message_recipient, subject, message_text)
            mycursor.execute(sql, val)
            mydb.commit()
            # reddit.redditor(str(message.author)).message('Successful tip!', response[0] + comment_footer)
            # status code 10 means the recipient has not requested silence, so send a message
            if response[1] == 10:
                message_recipient = response[3]
                subject = 'You just received a new Nano tip!'
                message_text = 'Somebody just tipped you ```%s Nano``` at your address %s. ' \
                               '[Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)\n\n' \
                                'To turn off these notifications, reply with "silence yes"' % (
                                response[2], response[4], response[5]) + comment_footer

                sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
                val = (message_recipient, subject, message_text)
                mycursor.execute(sql, val)
                mydb.commit()
                """
                x = reddit.redditor(response[3]). \
                    message('You just received a new Nano tip!',
                            'Somebody just tipped you ```%s Nano``` at your address %s. [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)\n\n'
                            'To turn off these notifications, reply with "silence yes"' % (
                                response[2], response[4], response[5]) + comment_footer)
                """
    elif subreddit_status == 'custom':
        # not sure what to do with this yet.
        pass


# These functions below handle the various messages the bot will receive
def handle_auto_receive(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    username = str(message.author)
    add_history_record(
        username=str(message.author),
        action='auto_receive',
        comment_id=message.name,
        comment_or_message='message',
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S')
        )

    parsed_text = message.body.replace('\\', '').split('\n')[0].split(' ')

    if len(parsed_text) < 2:
        response = "I couldn't parse your command. I was expecting 'auto_receive <yes/no>'. " \
                   "Be sure to check your spacing."
        return response


    if parsed_text[1] == 'yes':
        sql = "UPDATE accounts SET auto_receive = TRUE WHERE username = %s "
        val = (username, )
        mycursor.execute(sql, val)
        response = "auto_receive set to 'yes'."
    elif parsed_text[1] == 'no':
        sql = "UPDATE accounts SET auto_receive = FALSE WHERE username = %s"
        val = (username, )
        mycursor.execute(sql, val)
        response = "auto_receive set to 'no'. Use 'receive' to manually receive unpocketed transactions."
    else:
        response = "I did not see 'no' or 'yes' after 'auto_receive'. If you did type that, check your spacing."
    mydb.commit()

    return response


def handle_balance(message):
    username = str(message.author)
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message='message',
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
        action='balance',
        comment_id=message.name,
        comment_text=str(message.body)[:255]
    )
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result) > 0:
        results = check_balance(result[0][0])

        response = "At address %s:\n\nAvailable: %s Nano\n\nUnpocketed: %s Nano\n\nIf you have any unpocketed Nano, create a new " \
                   "message containing the word 'receive'.\n\nhttps://nanocrawler.cc/explorer/account/%s" % (result[0][0], results[0]/10**30, results[1]/10**30, result[0][0])

        return response
    return 'You do not have an open account yet'


def handle_create(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message='message',
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
        action='create',
        comment_id=message.name,
        comment_text=str(message.body)[:255]
    )

    username = str(message.author)
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result) is 0:
        address = add_new_account(username)
        response = welcome_create % (address, address)
        message_recipient = tip_bot_username
        subject = 'send'
        message_text = 'send 0.001 %s' % username
        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (message_recipient, subject, message_text)
        mycursor.execute(sql, val)
        mydb.commit()

        # reddit.redditor(message_recipient).message(subject, message_text)

    else:
        response = "It looks like you already have an account. In any case it is now **active**. Your Nano address is %s." \
                   "\n\nhttps://nanocrawler.cc/explorer/account/%s" % (result[0][0], result[0][0])
    return response


def handle_help(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        action='help',
        comment_or_message='message',
        comment_id=message.name,
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S')
        )
    response = help_text
    return response


def handle_history(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    username = str(message.author)
    parsed_text = message.body.replace('\\', '').split('\n')[0].split(' ')
    num_records = 10
    # print(len(parsed_text))
    # if there are more than 2 words, one of the words is a number for the number of records
    if len(parsed_text) >= 2:
        if parsed_text[1].lower() == 'nan' or ('inf' in parsed_text[1].lower()):
            response = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."
            return response
        try:
            num_records = int(parsed_text[1])
        except:
            response = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."
            return response

    # check that it's greater than 50
    if num_records > 50:
        num_records = 50

    # check if the user is in the database
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result) > 0:
        #open_or_receive(result[0][0], result[0][1])
        #balance = check_balance(result[0][0])
        add_history_record(
            username=username,
            action='history',
            amount=num_records,
            address=result[0][0],
            comment_or_message='message',
            comment_id=message.name,
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            comment_text=str(message.body)[:255]
        )
        #print(num_records)
        response = 'Here are your last %s historical records:\n\n' % num_records
        sql = "SELECT reddit_time, action, amount, comment_id, notes, recipient_username, recipient_address FROM history WHERE username=%s ORDER BY id DESC limit %s"
        val = (username, num_records)
        mycursor.execute(sql, val)
        results = mycursor.fetchall()
        for result in results:
            try:
                amount = result[2]
                if (result[1] == 'send') and amount:
                    amount = int(result[2]) / 10 ** 30
                    if result[4] == 'sent to registered redditor' or result[4] == 'new user created':
                        response += '%s: %s | %s Nano to %s | reddit object: %s | %s\n\n' % (result[0], result[1], amount, result[5], result[3], result[4])
                    elif result[4] == 'sent to registered address' or result[4] == 'sent to unregistered address':
                        response += '%s: %s | %s Nano to %s | reddit object: %s | %s\n\n' % (result[0], result[1], amount, result[6], result[3], result[4])
                elif (result[1] == 'send'):
                    response += '%s: %s | reddit object: %s | %s\n\n' % (
                    result[0], result[1], result[3], result[4])
                elif (result[1] == 'minimum') and amount:
                    amount = int(result[2])/10**30
                    response += '%s: %s | %s | %s | %s\n\n' % (result[0], result[1], amount, result[3], result[4])
                else:
                    response += '%s: %s | %s | %s | %s\n\n' % (result[0], result[1], amount, result[3], result[4])
            except:
                response += "Unparsed Record: Nothing is wrong, I just didn't parse this record properly.\n\n"

        return response
    else:
        add_history_record(
            username=username,
            action='history',
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            amount=num_records,
            comment_id=message.name,
            comment_text=str(message.body)[:255]
        )
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
        return response


def handle_minimum(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    # user may select a minimum tip amount to avoid spamming. Tipbot minimum is 0.001
    username = str(message.author)
    # find any accounts associated with the redditor
    parsed_text = message.body.replace('\\', '').split('\n')[0].split(' ')

    # there should be at least 2 words, a minimum and an amount.
    if len(parsed_text) < 2:
        response = "I couldn't parse your command. I was expecting 'minimum <amount>'. Be sure to check your spacing."
        return response
    # check that the minimum is a number

    if parsed_text[1].lower() == 'nan' or ('inf' in parsed_text[1].lower()):
        response = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."
        return response
    try:
        amount = float(parsed_text[1])
    except:
        response = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."
        return response

    # check that it's greater than 0.01
    if nano_to_raw(amount) < nano_to_raw(program_minimum):
        response = "Did not update. The amount you specified is below the program minimum of %s Nano."%program_minimum
        return response

    # check if the user is in the database
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result) > 0:
        #open_or_receive(result[0][0], result[0][1])
        #balance = check_balance(result[0][0])
        add_history_record(
            username=username,
            action='minimum',
            amount=nano_to_raw(amount),
            address=result[0][0],
            comment_or_message='message',
            comment_id=message.name,
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            comment_text=str(message.body)[:255]
        )
        sql = "UPDATE accounts SET minimum = %s WHERE username = %s"
        val = (str(nano_to_raw(amount)), username)
        mycursor.execute(sql, val)
        mydb.commit()
        response = "Updating tip minimum to %s"%amount
        return response
    else:
        add_history_record(
            username=username,
            action='minimum',
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            amount=nano_to_raw(amount),
            comment_id=message.name,
            comment_text=str(message.body)[:255]
        )
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
        return response


def handle_receive(message):
    """

    :param message:
    :return:
    """
    message_time = datetime.utcfromtimestamp(message.created_utc)
    username = str(message.author)
    # find any accounts associated with the redditor
    sql = "SELECT address, private_key FROM accounts WHERE username=%s"
    val = (username, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result) > 0:
        address = result[0][0]
        open_or_receive(address, result[0][1])
        balance = check_balance(address)
        add_history_record(
            username=username,
            action='receive',
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            address=address,
            comment_id=message.name,
            comment_or_message='message'
        )
        response = "At address %s, you currently have %s Nano available, and %s Nano unpocketed. If you have any unpocketed, create a new " \
                   "message containing the word 'receive'\n\nhttps://nanocrawler.cc/explorer/account/%s" % (
                   address, balance[0] / 10 ** 30, balance[1] / 10 ** 30, address)
        return response + comment_footer
    else:
        add_history_record(
            username=username,
            action='receive',
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            comment_id=message.name,
            comment_or_message='message'
        )
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
        return response + comment_footer


def handle_silence(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    username = str(message.author)
    add_history_record(
        username=str(message.author),
        action='silence',
        comment_or_message='message',
        comment_id=message.name,
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S')
        )

    parsed_text = message.body.replace('\\', '').split('\n')[0].split(' ')

    if len(parsed_text) < 2:
        response = "I couldn't parse your command. I was expecting 'silence <yes/no>'. Be sure to check your spacing."
        return response

    if parsed_text[1] == 'yes':
        sql = "UPDATE accounts SET silence = TRUE WHERE username = %s "
        val = (username, )
        mycursor.execute(sql, val)
        response = "Silence set to 'yes'. You will no longer receive tip notifications or be tagged by the bot."
    elif parsed_text[1] == 'no':
        sql = "UPDATE accounts SET silence = FALSE WHERE username = %s"
        val = (username, )
        mycursor.execute(sql, val)
        response = "Silence set to 'no'. You will receive tip notifications and be tagged by the bot in replies."
    else:
        response = "I did not see 'no' or 'yes' after 'silence'. If you did type that, check your spacing."
    mydb.commit()

    return response


def handle_send(message):
    """
    Extracts send command information from a PM command
    :param message:
    :return:
    """
    parsed_text = str(message.body).lower().replace('\\', '').split('\n')[0].split(' ')
    response = handle_send_nano(message, parsed_text, 'message')
    response = response[0]
    return response


def handle_message(message):
    # activate the account
    activate(message.author)
    response = 'not activated'
    message_body = str(message.body).lower()
    print("Body: **", message_body, "**")
    if message.body[0] == ' ':
        parsed_text = str(message.body[1:]).lower().replace('\\', '').split('\n')[0].split(' ')
    else:
        parsed_text = str(message.body).lower().replace('\\', '').split('\n')[0].split(' ')
    print("Parsed Text:", parsed_text)

    if (parsed_text[0].lower() == 'help') or (parsed_text[0].lower() == '!help'):
        print("Helping")
        subject = 'Nano Tipper - Help'
        response = handle_help(message)

    elif parsed_text[0].lower() == 'auto_receive':
        print("Setting auto_receive")
        subject = 'Nano Tipper - Auto Receive'
        response = handle_auto_receive(message)

    elif parsed_text[0].lower() == 'minimum':
        print("Setting Minimum")
        subject = 'Nano Tipper - Tip Minimum'
        response = handle_minimum(message)

    elif (parsed_text[0].lower() == 'create') or parsed_text[0].lower() == 'register':
        print("Creating")
        subject = 'Nano Tipper - Create'
        response = handle_create(message)

    elif parsed_text[0].lower() == 'private_key':
        print("private_keying")
        subject = 'Nano Tipper - Private Key'
        # handle_private_key(message)

    elif parsed_text[0].lower() == 'new_address':
        print("new address")
        subject = 'Nano Tipper - New Address'
        # handle_new_address(message)

    elif (parsed_text[0].lower() == 'send') or (parsed_text[0].lower() == 'withdraw'):
        subject = 'Nano Tipper - Send'
        print("send via PM")
        response = handle_send(message)

    elif parsed_text[0].lower() == 'history':
        print("history")
        subject = 'Nano Tipper - History'
        response = handle_history(message)

    elif parsed_text[0].lower() == 'silence':
        print("silencing")
        subject = 'Nano Tipper - Silence'
        response = handle_silence(message)

    elif (parsed_text[0].lower() == 'receive') or (parsed_text[0].lower() == 'pocket'):
        print("receive")
        subject = 'Nano Tipper - Receive'
        response = handle_receive(message)

    elif (parsed_text[0].lower() == 'balance') or (parsed_text[0].lower() == 'address'):
        print("balance")
        subject = 'Nano Tipper - Account Balance'
        response = handle_balance(message)
    elif parsed_text[0].lower() == 'test_welcome_tipped':
        subject = 'Nano Tipper - Welcome By Tip'
        response = welcome_tipped % (0.01, 'xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij', 'xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij')
    elif parsed_text[0].lower() == 'test_welcome_create':
        subject = 'Nano Tipper - Create'
        response = welcome_create % ('xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij', 'xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij')
        pass
    else:
        add_history_record(
            username=str(message.author),
            comment_text=str(message.body)[:255],
            comment_or_message='message',
            comment_id=message.name,
        )
        return None
    message_recipient = str(message.author)
    message_text = response + comment_footer
    sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
    val = (message_recipient, subject, message_text)
    mycursor.execute(sql, val)
    mydb.commit()
    # reddit.redditor(message_recipient).message(subject, message_text)


def handle_new_address(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message='message',
        action='new_address',
        comment_id=message.name,
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
        comment_text=str(message.body)[:255]
    )
    return 'not activated yet.'


def auto_receive():
    # print('running autoreceive')
    mycursor.execute("SELECT username, address, private_key FROM accounts WHERE auto_receive=TRUE")
    myresult = mycursor.fetchall()

    # for some reason, requesting 15 addresses takes a whole second
    addresses = [str(result[1]) for result in myresult]
    private_keys = [str(result[2]) for result in myresult]
    # pendings = get_pendings(addresses, threshold=nano_to_raw(program_minimum))
    pendings = get_pendings(addresses)
    # print(pendings)
    # print('got pendings.')
    for address, private_key in zip(addresses, private_keys):
        try:
            if pendings['blocks'][address]:
                print('Receiving these blocks: ', pendings['blocks'][address])
                # address, private_key, dictionary where the blocks are the keys
                open_or_receive_blocks(address, private_key, pendings['blocks'][address])
                # open_or_receive(address, private_key)
        except KeyError:
            pass
        except Exception as e:
            print(e)
    """


    for result in myresult:
        open_or_receive(result[1], result[2])
    """


def message_in_database(message):
    sql = "SELECT * FROM history WHERE comment_id = %s"
    val = (message.name, )
    mycursor.execute(sql, val)
    results = mycursor.fetchall()
    if len(results) > 0:
        print("previous message")
        print(message.name)
        for result in results:
            print('Result: ', results)
        return True
    return False


def check_inactive_transactions():
    t0 = time.time()
    print('running inactive script')
    mycursor.execute("SELECT username FROM accounts WHERE active IS NOT TRUE")
    myresults = mycursor.fetchall()
    inactivated_accounts = {item[0] for item in myresults}

    mycursor.execute("SELECT recipient_username FROM history WHERE action = 'send' AND hash IS NOT NULL AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 31 DAY) AND (return_status = 'cleared' OR return_status = 'warned')")
    results = mycursor.fetchall()
    tipped_accounts = {item[0] for item in results}

    tipped_inactivated_accounts = inactivated_accounts.intersection(tipped_accounts)
    print('Accounts on warning: ', sorted(tipped_inactivated_accounts))
    # scrolls through our inactive members and check if they have unclaimed tips
    for result in tipped_inactivated_accounts:
        # send warning messages on day 31
        sql = "SELECT * FROM history WHERE action = 'send' AND hash IS NOT NULL AND recipient_username = %s AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 31 DAY) AND return_status = 'cleared'"
        val = (result, )
        mycursor.execute(sql, val)
        txns = mycursor.fetchall()
        if len(txns) >= 1:
            print('generating a message for %s' % result)

            message_recipient = result
            subject = 'Please Activate Your Nano Tipper Account'
            message_text = "Somebody tipped you at least 30 days ago, but your account hasn't been activated yet.\n\nPlease activate your account by replying any command to this bot. If you do not, any tips 35 days or older will be returned.\n\n***\n\n"
            message_text += help_text
            sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
            val = (message_recipient, subject, message_text)
            mycursor.execute(sql, val)
            mydb.commit()
            for txn in txns:
                sql = "UPDATE history SET return_status = 'warned' WHERE id = %s"
                val = (txn[0], )
                mycursor.execute(sql, val)
                mydb.commit()
            # print(message_recipient, subject, message_text)

        # return transactions over 35 days old
        sql = "SELECT * FROM history WHERE action = 'send' AND hash IS NOT NULL AND recipient_username = %s AND `sql_time` <= SUBDATE( CURRENT_DATE, INTERVAL 35 DAY) AND return_status = 'warned'"
        val = (result, )
        mycursor.execute(sql, val)
        txns = mycursor.fetchall()
        if len(txns) >= 1:
            sql = "SELECT address, private_key FROM accounts WHERE username = %s"
            val = (result,)
            mycursor.execute(sql, val)
            inactive_results = mycursor.fetchall()
            address = inactive_results[0][0]
            private_key = inactive_results[0][1]

            for txn in txns:
                # set the pre-update message to 'return failed'. This will be changed to 'returned' upon success
                sql = "UPDATE history SET return_status = 'return failed' WHERE id = %s"
                val = (txn[0], )
                mycursor.execute(sql, val)
                mydb.commit()

                # get the transaction information and find out to whom we are returning the tip
                sql = "SELECT address FROM accounts WHERE username = %s"
                val = (txn[1], )
                mycursor.execute(sql, val)
                recipient_address = mycursor.fetchall()[0][0]
                print('History record: ', txn[0], address, private_key, txn[9], recipient_address)

                # send it back
                hash = send(address, private_key, int(txn[9]), recipient_address)['hash']
                print("Returning a transaction. ", hash)

                # update database if everything goes through
                sql = "UPDATE history SET return_status = 'returned' WHERE id = %s"
                val = (txn[0], )
                mycursor.execute(sql, val)
                mydb.commit()

                # send a message informing the tipper that the tip is being returned
                message_recipient = txn[1]
                subject = 'Returned your tip of %s to %s' % (int(txn[9])/10**30, result)
                message_text = "Your tip to %s for %s Nano was returned since the user never activated their account." % (result, int(txn[9])/10**30)
                sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
                val = (message_recipient, subject, message_text)
                mycursor.execute(sql, val)
                mydb.commit()

                add_history_record(hash=hash, amount=txn[9], notes='Returned transaction from history record %s'%txn[0])
    print(time.time()-t0)

# main loop
print('Starting up!')
t0 = time.time()
check_inactive_transactions()

for action_item in stream_comments_messages():
    # our 'stream_comments_messages()' generator will give us either messages or
    # (t1 = comment, t4 = message)
    # The bot handles these differently
    if action_item is None:
        pass
    elif message_in_database(action_item[1]):
        print("Previous message was found in stream...")
        print('Previous: ', action_item[1].author, ' - ', action_item[1].name, ' - ', action_item[1].body[:25])
    elif action_item[0] == 'comment':
        if action_item[1].body[0] == ' ':
            # remove any leading spaces. for convenience
            parsed_text = str(action_item[1].body[1:]).lower().replace('\\', '').split('\n')[0].split(' ')
        else:
            parsed_text = str(action_item[1].body).lower().replace('\\', '').split('\n')[0].split(' ')
        try:
            if (parsed_text[0] in tip_commands):
                print('*****************************************************')
                print(time.strftime('%Y-%m-%d %H:%M:%S'), 'Comment, beginning: ', action_item[1].author, ' - ', action_item[1].body[:20])

                if allowed_request(action_item[1].author, 30, 5) and not message_in_database(action_item[1]):
                    if tip_bot_on:
                        handle_comment(action_item[1])
                    else:
                        reddit.redditor(str(action_item[1].author)).message('Nano Tipper Currently Disabled', '[^(Nano Tipper is currently disabled)](https://www.reddit.com/r/nano_tipper/comments/astwp6/nano_tipper_status/)')
                else:
                    print('Too many requests for %s' % action_item[1].author)
                print('*****************************************************')
            elif (parsed_text[-2] in tip_commands):
                print('*****************************************************')
                print(time.strftime('%Y-%m-%d %H:%M:%S'), 'Comment, end: ', action_item[1].author, ' - ',
                      action_item[1].body[:20])

                if allowed_request(action_item[1].author, 30, 5) and not message_in_database(action_item[1]):
                    if tip_bot_on:
                        handle_comment(action_item[1], parsed_text=parsed_text[-2:])
                    else:
                        reddit.redditor(str(action_item[1].author)).message('Nano Tipper Currently Disabled',
                                                                            '[^(Nano Tipper is currently disabled)](https://www.reddit.com/r/nano_tipper/comments/astwp6/nano_tipper_status/)')
                else:
                    print('Too many requests for %s' % action_item[1].author)
                print('*****************************************************')
        except IndexError:
            pass


    elif action_item[0] == 'message':
        if action_item[1].author == tip_bot_username:
            if (action_item[1].name[:3] == 't4_') and (action_item[1].body[:11] == 'send 0.001 ') and not message_in_database(action_item[1]):
                print('*****************************************************')
                print(time.strftime('%Y-%m-%d %H:%M:%S'), 'Faucet Tip: ', action_item[1].author, ' - ', action_item[1].body[:20])
                handle_message(action_item[1])
                print('*****************************************************')
            else:
                print('ignoring nano_tipper message')

        elif not allowed_request(action_item[1].author, 30, 5):
            print('Too many requests for %s' % action_item[1].author)
        else:
            if tip_bot_on:
                #parse out the text
                if action_item[1].name[:3] == 't4_' and not message_in_database(action_item[1]):

                    print('*****************************************************')
                    print(time.strftime('%Y-%m-%d %H:%M:%S'), 'Message: ', action_item[1].author, ' - ', action_item[1].body[:20])
                    handle_message(action_item[1])
                    print('*****************************************************')
            else:
                action_item[1].reply('[^(Nano Tipper is currently disabled)](https://www.reddit.com/r/nano_tipper/comments/astwp6/nano_tipper_status/)')

    elif action_item[0] == 'username mention':
        # print('Printing Username mention: ', parsed_text[0])
        if action_item[1].body[0] == ' ':
            # remove any leading spaces. for convenience
            parsed_text = str(action_item[1].body[1:]).lower().replace('\\', '').split('\n')[0].split(' ')
        else:
            parsed_text = str(action_item[1].body).lower().replace('\\', '').split('\n')[0].split(' ')
        print(parsed_text[0])

        try:
            if (parsed_text[0] == '/u/%s'%tip_bot_username) or (parsed_text[0] == 'u/%s' % tip_bot_username):
                print('*****************************************************')
                print(time.strftime('%Y-%m-%d %H:%M:%S'), 'Username Mention: ', action_item[1].author, ' - ', action_item[1].body[:20])
                if allowed_request(action_item[1].author, 30, 5) and not message_in_database(action_item[1]):
                    if tip_bot_on:
                        handle_comment(action_item[1])
                        pass
                    else:
                        reddit.redditor(str(action_item[1].author)).message('Nano Tipper Currently Disabled',
                                                                            '[^(Nano Tipper is currently disabled)](https://www.reddit.com/r/nano_tipper/comments/astwp6/nano_tipper_status/)')
                else:
                    print('Too many requests for %s' % action_item[1].author)
                print('*****************************************************')
            elif (parsed_text[-2] == '/u/%s'%tip_bot_username) or (parsed_text[-2] == 'u/%s' % tip_bot_username):
                print('*****************************************************')
                print(time.strftime('%Y-%m-%d %H:%M:%S'), 'Username Mention: ', action_item[1].author, ' - ',
                      action_item[1].body[:20])
                if allowed_request(action_item[1].author, 30, 5) and not message_in_database(action_item[1]):
                    if tip_bot_on:
                        handle_comment(action_item[1], parsed_text=parsed_text[-2:])
                    else:
                        reddit.redditor(str(action_item[1].author)).message('Nano Tipper Currently Disabled',
                                                                            '[^(Nano Tipper is currently disabled)](https://www.reddit.com/r/nano_tipper/comments/astwp6/nano_tipper_status/)')
                else:
                    print('Too many requests for %s' % action_item[1].author)
                print('*****************************************************')
        except IndexError:
            pass

    # run the inactive script at the end of the loop
    if time.time()-t0 > 3600:
        t0 = time.time()
        check_inactive_transactions()


