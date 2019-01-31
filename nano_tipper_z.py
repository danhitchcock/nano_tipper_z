import praw
import time
from datetime import datetime
from time import sleep
from rpc_bindings import send, open_account, generate_account, generate_qr, nano_to_raw, receive_all, send_all, \
    check_balance, validate_address, open_or_receive, get_pendings
import mysql.connector

# initiate the reddit object library
reddit = praw.Reddit('bot1')
subreddit = reddit.subreddit("nano_tipper_z+cryptocurrency247+nanotrade+nanocurrency")

# access the sql library
with open('sql_password.txt') as f:
    sql_password = f.read()
mydb = mysql.connector.connect(user='root', password=sql_password,
                              host='localhost',
                              auth_plugin='mysql_native_password', database='nano_tipper_z')
mycursor = mydb.cursor()

# a few globals
program_minimum = 0.0001
recipient_minimum = 0.0001
toggle_receive = True
comment_footer = """\n\n
[*^(Get Free Nano!)*](https://nano-faucet.org/)*^( | )*
[*^(Nano_Tipper_Z)*](https://github.com/danhitchcock/nano_tipper_z)*^( | )*
[*^(Nano)*](https://nano.org)*^( | )*
[*^(Spend Nano)*](https://usenano.org/)*^( | )*
[*^(Nano Projects)*](https://nanocenter.org)*^( | This program is in early beta testing, 
funds are not safe.)*"""

help_text = """
Welcome to Nano Tipper Z Bot v0.1. Nano Tipper Z is a Reddit tip bot which handles on-chain tips! 
[Visit us on GitHub](https://github.com/danhitchcock/nano_tipper_z) for more information on its use. 
To use the bot, create a new message with any of the following commands in the message body:\n
    'create' - Create a new account if one does not exist
    'private_key' - (disabled) Retrieve your account private key
    'new_address' - (disabled) If you feel this address was compromised, create a new account and key
    'send <amount or all> <user/address>' - Send Nano to a reddit user or an address
    'receive' - Receive all pending transactions (if autoreceive is set to 'no')
    'balance' or 'address' - Retrieve your account balance. Includes both pocketed and unpocketed transactions
    'minimum <amount>' - (default 0.0001) Sets a minimum amount for receiving tips
    'auto_receive <yes/no>' - (default 'yes') Automatically pockets transactions. Checks every 12 seconds
    'silence <yes/no>' - (disabled, default 'no') stops uncommanded notifications from the bot
    'history' - (disabled) Grabs the last 20 records of your account history
    'help' - Get this help message\n
If you have any questions or bug fixes, please contact /u/zily88.\n""" + comment_footer

# generator to stream comments and messages to the main loop at the bottom, and contains the auto_receive functionality.
# Maybe this wasn't necessary, but I never get to use generators.
# To check for new messages and comments, the function scans the subreddits and inbox every 6 seconds and builds a
# set of current message. I compare the old set with the new set.
def stream_comments_messages():
    previous_comments = {comment for comment in subreddit.comments()}
    previous_messages = {message for message in reddit.inbox.unread()}
    print('Received first stream!')
    global toggle_receive
    while True:
        if toggle_receive:
            auto_receive()
        toggle_receive = not toggle_receive
        sleep(6)

        updated_comments = {comment for comment in subreddit.comments()}
        new_comments = updated_comments - previous_comments
        previous_comments = updated_comments

        # check for new messages
        updated_messages = {message for message in reddit.inbox.unread()}
        new_messages = updated_messages - previous_messages
        previous_messages = updated_messages

        # send anything new to our main program
        # also, check the message type. this will prevent posts from being seen as messages
        if len(new_comments) >= 1:
            for new_comment in new_comments:
                # if new_comment starts with 't1_'
                if new_comment.name[:3] == 't1_':
                    yield ('comment', new_comment)
        if len(new_messages) >= 1:
            for new_message in new_messages:
                # if message starts with 't4_'
                if new_message.name[:3] == 't4_':
                    yield ('message', new_message)

        else:
            yield None


def update_history():
    return None


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


def add_new_account(username):
    address = generate_account()
    private = address['private']
    address = address['account']
    sql = "INSERT INTO accounts (username, private_key, address, minimum, auto_receive) VALUES (%s, %s, %s, %s, %s)"
    val = (username, private, address, nano_to_raw(0.01), True)
    mycursor.execute(sql, val)
    mydb.commit()
    return address


def handle_create(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message='message',
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
        action='create',
        comment_text=str(message.body)[:255]
    )

    username = str(message.author)
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result) is 0:
        address = add_new_account(username)
        response = "Hi, welcome to Nano Tipper Z! Your Nano address is %s.\n\n"\
                   "To load Nano, try the free [Nano Faucet](https://nano-faucet.org/), or deposit some " \
                   "(click on Nanode for a QR code), " \
                   "or receive a tip from a fellow redditor!\n\n"\
                   "To withdraw your Nano to your own wallet, reply: ```send <amount> <address>```.\n\n"\
                   'Or to send to another redditor: ```send <amount> <redditor username>```.\n\n'\
                   'Or tip on a reddit post/comment: ```!nano_tip <amount>```.\n\n'\
                   'View your account on Nanode: https://www.nanode.co/account/%s\n\nHere are some additional resources and usage notes:\n***' % (address, address)
    else:
        response = "It looks like you already have an account made. Your Nano address is %s." \
                   "\n\nhttps://www.nanode.co/account/%s" % (result[0][0], result[0][0])
    x = reddit.redditor(username).message('Nano Tipper Z: Account Creation', response + help_text)
    # message.reply(response)


def handle_private_key(message):
    author = str(message.author)
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message='message',
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
        action='private_key',
        comment_text=str(message.body)[:255]
    )
    sql = "SELECT address, private_key FROM accounts WHERE name=%s"
    val = (author, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result) > 0:
        response = 'Your account: %s\n\nYour private key: %s'%(result[0][0],result[0][1])
        x = reddit.redditor(username).message('New Private Key', response)
        return None
    else:
        x = reddit.redditor(username).message("No account found.","You do not currently have an account open."
                                                                "To create one, respond with the text 'create' in the message body.")
        return None


def handle_balance(message):
    username = str(message.author)
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message='message',
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
        action='balance',
        comment_text=str(message.body)[:255]
    )
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username, )
    mycursor.execute(sql, val)
    result = mycursor.fetchall()
    if len(result)>0:
        results = check_balance(result[0][0])

        response = "At address %s, you currently have %s Nano available, and %s Nano unpocketed. If you have any unpocketed, create a new " \
                   "message containing the word 'receive'\n\nhttps://www.nanode.co/account/%s" % (result[0][0], results[0]/10**30, results[1]/10**30, result[0][0])
        reddit.redditor(username).message('Nano Tipper Z account balance', response + comment_footer)
        return None

    reddit.redditor(username).message('Nano Tipper Z: No account registered.', 'You do not have an open account yet' + comment_footer)


def handle_new_address(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message='message',
        action='new_address',
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
        comment_text=str(message.body)[:255]
    )
    message.reply('not activated yet.')


def handle_send(message):
    parsed_text = str(message.body).lower().replace('\\', '').split('\n')[0].split(' ')
    response = handle_send_nano(message, parsed_text, 'message')
    message.reply(response + comment_footer)


# amount is converted to raw in this function!
def handle_send_nano(message, parsed_text, comment_or_message):
    # declare a few variables so I can keep track of them. They will be redefined
    username = str(message.author)  # the sender
    private_key = ''  # the sender's private key
    user_or_address = ''  # either 'user' or 'address', depending on how the recipient was specified
    recipient = ''  # could be an address or redditor. Will be renamed recipient_username or recipient_address below
    recipient_username = ''  # the recipient username, should one exist
    recipient_address = ''  # the recipient nano address
    message_time = datetime.utcfromtimestamp(message.created_utc) # time the reddit message was created

    entry_id = add_history_record(
        username=username,
        action='send',
        comment_or_message=comment_or_message,
        comment_id=message.id,
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
        comment_text=str(message.body)[:255]
        )

    # check if the message body was parsed into 2 or 3 words. If it wasn't, update the history db
    # with a failure and return the message. If the length is 2 (meaning recipient is parent author) we will
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
        return 'Could not read your tip or send command, or find an amount. Be sure the amount and recipient are separated by a space.'


    # check that the tip is a number or 'all'
    if parsed_text[1].lower() == 'nan' or ('inf' in parsed_text[1].lower()):
        sql = "UPDATE history SET notes = %s WHERE id = %s"
        val = ('could not parse amount', entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        return "Could not read your tip or send amount. Is '%s' a number?" % parsed_text[1]
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
            return 'You do not have a tip bot account yet. To create one, send me a PM containing the' \
                   " text 'create' in the message body, or get a tip from a fellow redditor!"
    else:
        try:
            amount = nano_to_raw(float(parsed_text[1]))
        except:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ('could not parse amount', entry_id)
            mycursor.execute(sql, val)
            mydb.commit()
            return "Could not read your tip or send amount. Is '%s' a number?" % parsed_text[1]

    if amount < nano_to_raw(program_minimum):
        sql = "UPDATE history SET notes = %s WHERE id = %s"
        val = ('amount below program limit', entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        return 'You must send amounts of Nano above the program minimum of %s Nano.' % program_minimum

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

        return 'You do not have a tip bot account yet. To create one, send me a PM containing the'\
               " text 'create' in the message body, or get a tip from a fellow redditor!"
    else:
        address = result[0][0]
        private_key = result[0][1]
        results = check_balance(result[0][0])
        if amount > results[0]:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ('insufficient funds', entry_id)
            mycursor.execute(sql, val)
            mydb.commit()
            return 'You have insufficient funds. Your account has %s Nano pocketed (+%s Nano unpocketed) and you are '\
                          'trying to send %s. If you have unpocketed funds, create a new message containing the text'\
                          ' "receive" to pocket your incoming money.'%(results[0]/10**30, results[1]/10**30, amount/10**30)

    # if there was only the command and the amount, we need to find the recipient.
    # if it was a comment, the recipient is the parent author
    # if it was a message, the program will respond with an error
    if len(parsed_text) == 2:
        if comment_or_message == 'comment':
            recipient = str(message.parent().author)
        else:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ("no recipient specified", entry_id)
            mycursor.execute(sql, val)
            mydb.commit()
            return "You must specify an amount and a user."

    # remove the /u/ if a redditor was specified
    if recipient[:3].lower() == '/u/':
        recipient = recipient[3:]

    # or the u/
    if recipient[:2].lower() == 'u/':
        recipient = recipient[2:]
    print(recipient)
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
                return '%s is neither a valid address nor a redditor' % recipient
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
            return "Could not find redditor %s. Make sure you aren't writing or copy/pasting markdown." % recipient

    # at this point:
    # 'amount' is a valid positive number in raw and above the program minimum
    # 'username' has a valid account and enough Nano for the tip
    # 'user_or_address' is either 'user' or 'address',
    # 'recipient' is either a valid redditor or a valid Nano address

    user_minimum = -1
    # if a user is specified, reassign that as the username
    if user_or_address == 'user':
        #try to get the username information
        recipient_username = recipient
        sql = "SELECT minimum, address FROM accounts WHERE username = %s"
        val = (recipient_username,)
        mycursor.execute(sql, val)
        myresult = mycursor.fetchall()
        # if there is a result, pull out the minimum (in raw) and nano address for the recipient
        if len(myresult) > 0:
            user_minimum = int(myresult[0][0])
            recipient_address = myresult[0][1]
    else:
        # if the recipient is an address, check if they have an account
        recipient_address = recipient
        recipient_username = check_registered_by_address(recipient_address)
        if recipient_username:
            sql = "SELECT minimum, address FROM accounts WHERE username = %s"
            val = (recipient_username,)
            mycursor.execute(sql, val)
            myresult = mycursor.fetchall()
            user_minimum = int(myresult[0][0])

    # if either we had an account or address which has been registered, recipient_address and recipient_username will
    # have values instead of being ''. We will check the minimum
    if (user_minimum >= 0) and recipient_address and recipient_username:
        if amount < user_minimum:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ("below user minimum", entry_id)
            mycursor.execute(sql, val)
            mydb.commit()
            return "Sorry, the user has set a tip minimum of %s. " \
                   "Your tip of %s is below this amount." % (user_minimum/10**30, amount/10**30)

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
        sent = send(address, private_key, amount, recipient_address)
        sql = "UPDATE history SET hash = %s WHERE id = %s"
        val = (sent['hash'], entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        if comment_or_message == "message":
            # if it was a PM, send a message to notify the recipient
            # also check to see if the recipient has elected 'silence'
            x = reddit.\
                redditor(recipient_username).\
                message('You just received a new Nano tip!',
                        'Somebody just tipped you %s Nano at your address %s. Your new account balance will be '
                        '%s received and %s unpocketed. [Transaction on Nanode](https://www.nanode.co/block/%s)\n\n' % (
                        amount / 10 ** 30, recipient_address, receiving_new_balance[0] / 10 ** 30,
                        (receiving_new_balance[1] / 10 ** 30 + amount / 10 ** 30), sent['hash']) + comment_footer)


        if user_or_address == 'user':
            return "Sent ```%s Nano``` to /u/%s -- [Transaction on Nanode](https://www.nanode.co/block/%s)" % (amount / 10 ** 30, recipient_username, sent['hash'])
        else:
            return "Sent ```%s Nano``` to [%s](https://www.nanode.co/account/%s) -- [Transaction on Nanode](https://www.nanode.co/block/%s)" % (amount / 10 ** 30, recipient_address, recipient_address, sent['hash'])

    elif recipient_address:
        # or if we have an address but no account, just send
        sql = "UPDATE history SET notes = %s, address = %s, username = %s, recipient_address = %s, amount = %s WHERE id = %s"
        val = (
            'sent to unregistered address', address, username, recipient_address, str(amount), entry_id)
        mycursor.execute(sql, val)
        mydb.commit()

        print("Sending Unregistered Address: ", address, private_key, amount, recipient_address)
        sent = send(address, private_key, amount, recipient_address)
        sql = "UPDATE history SET hash = %s WHERE id = %s"
        val = (sent['hash'], entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        return "Sent ```%s Nano``` to [%s](https://www.nanode.co/account/%s). -- [Transaction on Nanode](https://www.nanode.co/block/%s)" % (amount/ 10 ** 30, recipient_address, recipient_address, sent['hash'])
    else:
        # create a new account for redditor
        recipient_address = add_new_account(recipient_username)

        x = reddit. \
            redditor(recipient_username). \
            message('Congrats on receiving your first Nano Tip!',
                    'Welcome to Nano Tip Bot! You have just received a Nano tip in the amount of ```| %s Nano |``` at your address '
                    '%s.\n\n To withdraw your Nano to your own wallet, reply: ```send <amount> <address>```.\n\n'
                    'Or to send to another redditor: ```send <amount> <redditor username>```.\n\n'
                    'Or set your minimum tip amount to prevent spam: ```minimum <amount>```.\n\n'
                    'Or tip on a reddit post/comment: ```!nano_tip <amount>```.\n\n'
                    'View your account on Nanode: https://www.nanode.co/account/%s\n\nHere are some additional resources and usage notes:\n***'% (
                    amount/ 10 ** 30, recipient_address, recipient_address) + help_text)

        sql = "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, recipient_address = %s, amount = %s WHERE id = %s"
        val = ("new user created", address, username, recipient_username, recipient_address,
               str(amount), entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        sent = send(address, private_key, amount, recipient_address)
        sql = "UPDATE history SET hash = %s WHERE id = %s"
        val = (sent['hash'], entry_id)
        mycursor.execute(sql, val)
        mydb.commit()
        print("Sending New Account Address: ", address, private_key, amount, recipient_address, recipient_username)
        return "Creating a new account for /u/%s and "\
                      "sending ```%s Nano```. [Transaction on Nanode](https://www.nanode.co/block/%s)" % (recipient_username, amount / 10 **30, sent['hash'])


def handle_receive(message):
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
            comment_or_message='message'
        )
        response = "At address %s, you currently have %s Nano available, and %s Nano unpocketed. If you have any unpocketed, create a new " \
                   "message containing the word 'receive'\n\nhttps://www.nanode.co/account/%s" % (
                   address, balance[0] / 10 ** 30, balance[1] / 10 ** 30, address)
        message.reply(response + comment_footer)
    else:
        add_history_record(
            username=username,
            action='receive',
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            comment_or_message='message'
        )
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
        message.reply(response + comment_footer)


# amount is a float in Nano in this function!
def handle_minimum(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    # user may select a minimum tip amount to avoid spamming. Tipbot minimum is 0.001
    username = str(message.author)
    # find any accounts associated with the redditor
    parsed_text = message.body.replace('\\', '').split('\n')[0].split(' ')

    # there should be at least 2 words, a minimum and an amount.
    if len(parsed_text) < 2:
        response = "I couldn't parse your command. I was expecting 'minimum <amount>'. Be sure to check your spacing."
        message.reply(response)
        return None
    # check that the minimum is a number

    if parsed_text[1].lower() == 'nan' or ('inf' in parsed_text[1].lower()):
        response = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."
        message.reply(response)
        return None
    try:
        amount = float(parsed_text[1])
    except:
        response = "'%s' didn't look like a number to me. If it is blank, there might be extra spaces in the command."
        message.reply(response)
        return None

    # check that it's greater than 0.01
    if nano_to_raw(amount) < nano_to_raw(program_minimum):
        response = "Did not update. The amount you specified is below the program minimum of %s Nano."%program_minimum
        message.reply(response)
        return None

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
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            comment_text=str(message.body)[:255]
        )
        sql = "UPDATE accounts SET minimum = %s WHERE username = %s"
        val = (str(nano_to_raw(amount)), username)
        mycursor.execute(sql, val)
        mydb.commit()
        response = "Updating tip minimum to %s"%amount
        message.reply(response)
    else:
        add_history_record(
            username=username,
            action='minimum',
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            amount=nano_to_raw(amount),
            comment_text=str(message.body)[:255]
        )
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
        message.reply(response)


def handle_help(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        action='help',
        comment_or_message='message',
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S')
        )
    response = help_text
    message.reply(response)


def handle_comment(message):
    # remove an annoying extra space that might be in the front
    if message.body[0] == ' ':
        parsed_text = str(message.body[1:]).lower().replace('\\', '').split('\n')[0].split(' ')
    else:
        parsed_text = str(message.body).lower().replace('\\', '').split('\n')[0].split(' ')
    response = handle_send_nano(message, parsed_text, 'comment')
    message.reply(response + comment_footer)


def handle_auto_receive(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    username = str(message.author)
    add_history_record(
        username=str(message.author),
        action='auto_receive',
        comment_or_message='message',
        reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S')
        )

    parsed_text = message.body.replace('\\', '').split('\n')[0].split(' ')

    if len(parsed_text) < 2:
        response = "I couldn't parse your command. I was expecting 'auto_receive <yes/no>'. Be sure to check your spacing."
        message.reply(response)
        return None

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

    message.reply(response)


def handle_message(message):
    message_body = str(message.body).lower()
    print("Body: **", message_body, "**")
    if message.body[0] == ' ':
        parsed_text = str(message.body[1:]).lower().replace('\\', '').split('\n')[0].split(' ')
    else:
        parsed_text = str(message.body).lower().replace('\\', '').split('\n')[0].split(' ')
    print("Parsed Text:", parsed_text)

    if parsed_text[0].lower() == 'help':
        print("Helping")
        handle_help(message)

    elif parsed_text[0].lower() == 'auto_receive':
        print("Setting auto_receive")
        handle_auto_receive(message)

    elif parsed_text[0].lower() == 'minimum':
        print("Setting Minimum")
        handle_minimum(message)

    elif (parsed_text[0].lower() == 'create') or parsed_text[0].lower() == 'register':
        print("Creating")
        handle_create(message)

    elif parsed_text[0].lower() == 'private_key':
        print("private_keying")
        # handle_private_key(message)

    elif parsed_text[0].lower() == 'new_address':
        print("new address")
        # handle_new_address(message)

    elif parsed_text[0].lower() == 'send':
        print("send via PM")
        handle_send(message)

    elif (parsed_text[0].lower() == 'receive') or (parsed_text[0].lower() == 'pocket'):
        print("receive")
        handle_receive(message)

    elif (parsed_text[0].lower() == 'balance') or (parsed_text[0].lower() == 'address'):
        print("balance")
        handle_balance(message)
    else:
        add_history_record(
            username=str(message.author),
            comment_text=str(message.body)[:255],
            comment_or_message='message',
        )


def auto_receive():
    mycursor.execute("SELECT username, address, private_key FROM accounts WHERE auto_receive=TRUE")
    myresult = mycursor.fetchall()

    # for some reason, requesting 15 addresses takes a whole second
    addresses = [str(result[1]) for result in myresult]
    private_keys = [str(result[2]) for result in myresult]
    pendings = get_pendings(addresses)
    for address, private_key in zip(addresses, private_keys):
        try:
            if pendings['blocks'][address]:
                print('Receiving these blocks: ', pendings['blocks'][address])
                open_or_receive(address, private_key)
        except KeyError:
            pass
    """


    for result in myresult:
        open_or_receive(result[1], result[2])
    """


def allowed_request(username, seconds=30, num_requests=5):
    """
    :param username: str (username)
    :param seconds: int (time period to allow the num_requests)
    :param num_requests: int (number of allowed requests)
    :return:
    """
    #return True
    sql = 'SELECT sql_time FROM history WHERE username=%s'
    val = (str(username), )
    mycursor.execute(sql, val)
    myresults = mycursor.fetchall()
    if len(myresults) < num_requests:
        return True
    else:
        return (datetime.fromtimestamp(time.time()) - myresults[-5][0]).total_seconds() > seconds


# main loop
for action_item in stream_comments_messages():
    # every 86400 seconds (once a day) scan for 30 day old tips to inactive accounts
    # get transactions to those accounts which are 30 days or older
    # reverse them

    # our 'stream_comments_messages()' generator will give us either messages or comments by checking the tag on the message name
    # (t1 = comment, t4 = message)
    # The bot handles these differently
    if action_item is None:
        pass
        #print('No news.')
    elif action_item[0] == 'comment':
        if action_item[1].body[0]==' ':
            parsed_text = str(action_item[1].body[1:]).lower().replace('\\', '').split('\n')[0].split(' ')
        else:
            parsed_text = str(action_item[1].body).lower().replace('\\', '').split('\n')[0].split(' ')
        # print('Parsed comment: ', parsed_text)
        if parsed_text[0] == r'!nano_tip':
            print('*****************************************************')
            print('Comment: ', action_item[1].author, ' - ', action_item[1].body[:20])
            print('*****************************************************')
            if allowed_request(action_item[1].author, 30, 5):
                handle_comment(action_item[1])
            else:
                print('Too many requests for %s' % action_item[1].author)

    elif action_item[0] == 'message':
        if action_item[1].author == 'nano_tipper_z':
            pass
        elif not allowed_request(action_item[1].author, 30, 5):
            print('Too many requests for %s' % action_item[1].author)
        else:
            print(time.strftime('%Y-%m-%d %H:%M:%S'))
            print('*****************************************************')
            print('Comment: ', action_item[1].author, ' - ', action_item[1].body[:20])
            print('*****************************************************')
            handle_message(action_item[1])



