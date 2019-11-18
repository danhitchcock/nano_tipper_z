import time
from datetime import datetime
import shared
from rpc_bindings import generate_account, nano_to_raw, check_balance, validate_address
from rpc_bindings import send_w as send
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import requests

# mycursor = shared.mycursor
# mydb = shared.mydb
# recipient_minimum = shared.recipient_minimum
# excluded_redditors = shared.excluded_redditors
# program_minimum = shared.program_minimum
# reddit = shared.reddit
# new_tip = shared.new_tip
# comment_footer = shared.comment_footer
# welcome_tipped = shared.welcome_tipped


def add_history_record(username=None, action=None, sql_time=None, address=None, comment_or_message=None,
                       recipient_username=None, recipient_address=None, amount=None, hash=None, comment_id=None,
                       notes=None, reddit_time=None, comment_text=None):
    if sql_time is None:
        sql_time = time.strftime('%Y-%m-%d %H:%M:%S')

    sql = "INSERT INTO history (username, action, sql_time, address, comment_or_message, recipient_username, " \
          "recipient_address, amount, hash, comment_id, notes, reddit_time, comment_text) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

    val = (username, action, sql_time, address, comment_or_message, recipient_username, recipient_address, amount,
           hash, comment_id, notes, reddit_time, comment_text)

    shared.mycursor.execute(sql, val)
    shared.mydb.commit()
    return shared.mycursor.lastrowid

def parse_text(text):
    return(text.lower().replace('\\', '').replace('\n', ' ').split(' '))


def add_new_account(username):
    address = generate_account()
    private = address['private']
    address = address['account']
    sql = "INSERT INTO accounts (username, private_key, address, minimum, auto_receive, silence, active, percentage) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    val = (username, private, address, nano_to_raw(shared.recipient_minimum), True, False, False, 10)
    shared.mycursor.execute(sql, val)
    shared.mydb.commit()
    return address


def activate(author):
    sql = "UPDATE accounts SET active = TRUE WHERE username = %s"
    val = (str(author),)
    shared.mycursor.execute(sql, val)
    shared.mydb.commit()


def allowed_request(username, seconds=30, num_requests=5):
    """ Spam prevention
    :param username: str (username)
    :param seconds: int (time period to allow the num_requests)
    :param num_requests: int (number of allowed requests)
    :return:
    """
    sql = 'SELECT sql_time FROM history WHERE username=%s'
    val = (str(username), )
    shared.mycursor.execute(sql, val)
    myresults = shared.mycursor.fetchall()
    if len(myresults) < num_requests:
        return True
    else:
        return (datetime.fromtimestamp(time.time()) - myresults[-5][0]).total_seconds() > seconds


def check_registered_by_address(address):
    address = address.split('_')[1]

    sql = "SELECT username FROM accounts WHERE address=%s"
    val = ('xrb_' + address, )
    shared.mycursor.execute(sql, val)
    result = shared.mycursor.fetchall()
    if len(result) > 0:
        return result[0][0]

    sql = "SELECT username FROM accounts WHERE address=%s"
    val = ('nano_' + address, )
    shared.mycursor.execute(sql, val)
    result = shared.mycursor.fetchall()
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
        shared.mycursor.execute(sql, val)
        myresult = shared.mycursor.fetchall()
        if len(myresult) > 0:
            user_minimum = int(myresult[0][0])
            silence = myresult[0][2]
            if not recipient_address:
                recipient_address = myresult[0][1]
    return user_minimum, recipient_address, silence


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

    # set the account to activated it if it was a new one
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
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()
        response ='Could not read your tip command.'
        return [response, 0, None, None, None, None]


    # check if there was an attempt to send via a currency conversion
    if len(parsed_text)>=3:
        if parsed_text[2].lower() in shared.excluded_redditors:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ('conversion syntax error', entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
            response = "It wasn't clear if you were trying to perform a currency conversion or not. If so, be sure there is no space between the amount and currency. Example: '!ntip 0.5USD'"
            return [response, 1, None, None, None, None]


    # check if it's a currency code and parse the amount accordingly
    conversion = 1
    if parsed_text[1][-3:].lower() in shared.excluded_redditors:

        currency = parsed_text[1][-3:].upper()
        url = 'https://min-api.cryptocompare.com/data/price?fsym={}&tsyms={}'.format('NANO', currency)
        try:
            results = requests.get(url, timeout=1)
            results = json.loads(results.text)

            conversion = float(results[currency])
            amount = parsed_text[1][:-3].lower()

        except requests.exceptions.Timeout:
            amount = 'Could not reach conversion server.'
        except:
            amount = 'Currency [%s] not supported.'%currency.upper()
    else:
        amount = parsed_text[1].lower()

    # amount will be a string at this point. If the currency conversion failed, it will be an error message
    # check that the tip is a number or 'all'
    # if the amount is 'all', we need to lookup the users account balance
    if amount == 'nan' or ('inf' in amount):
        sql = "UPDATE history SET notes = %s WHERE id = %s"
        val = ('could not parse amount', entry_id)
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()
        response = "Could not read your tip or send amount. Is '%s' a number?" % parsed_text[1]
        return [response, 1, None, None, None, None]
    elif str(amount) == 'all':
        sql = "SELECT address FROM accounts WHERE username = %s"
        val = (username,)
        shared.mycursor.execute(sql, val)
        result = shared.mycursor.fetchall()
        if len(result) > 0:
            address = result[0][0]
            balance = check_balance(address)
            amount = balance[0]
        else:
            response = 'You do not have a tip bot account yet. PM me "create".'
            return [response, 2, None, None, None, None]
    else:
        try:
            amount = nano_to_raw(float(amount)/conversion)
        except:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ('could not parse amount', entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
            response = "Could not read your tip or send amount. Is '%s' a number, or is the currency code valid?" % amount
            return [response, 1, None, None, None, None]

    if amount < nano_to_raw(shared.program_minimum):
        sql = "UPDATE history SET notes = %s WHERE id = %s"
        val = ('amount below program limit', entry_id)
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()
        response = 'Program minimum is %s Nano.' % shared.program_minimum
        return [response, 3, amount / 10**30, None, None, None]

    # check to see if it is a friendly subreddit
    if comment_or_message == 'comment':
        sql = 'SELECT status FROM subreddits WHERE subreddit=%s'
        val = (str(message.subreddit).lower(), )
        shared.mycursor.execute(sql, val)
        results = shared.mycursor.fetchall()
        if len(results) == 0:
            subreddit_status = 'hostile'
        else:
            subreddit_status = results[0][0]
        if subreddit_status != 'friendly':
            if amount < nano_to_raw(1):
                response = 'To tip in unfamiliar subreddits, the tip amount must be 1 Nano or more. You attempted to tip %s Nano'%(amount/10**30)
                return [response, 3, None, None, None, None]


    # check if author has an account, and if they have enough funds
    sql = "SELECT address, private_key FROM accounts WHERE username=%s"
    val = (username, )
    shared.mycursor.execute(sql, val)
    result = shared.mycursor.fetchall()
    if len(result) < 1:
        sql = "UPDATE history SET notes = %s WHERE id = %s"
        val = ('sender does not have an account', entry_id)
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()
        response = 'You do not have a tip bot account yet. PM me "create".'
        return [response, 2, amount / 10 ** 30, None, None, None]
    else:
        address = result[0][0]
        private_key = result[0][1]
        results = check_balance(result[0][0])
        if amount > results[0]:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ('insufficient funds', entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
            response = 'You have insufficient funds. Please check your balance.'
            return [response, 4, amount / 10 ** 30, None, None, None]

    # if the command was from a PM, extract the recipient username or address
    # otherwise it was a comment, and extract the parent author
    # or if it was a public nanocenter donation, extract the project name
    if comment_or_message == 'message':
        if len(parsed_text) == 2:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ("no recipient specified", entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
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
                    dummy = getattr(shared.reddit.redditor(recipient), 'is_suspended', False)
                    user_or_address = 'user'
                except:
                    # not a valid address or a redditor
                    sql = "UPDATE history SET notes = %s WHERE id = %s"
                    val = ('invalid address or address-like redditor does not exist', entry_id)
                    shared.mycursor.execute(sql, val)
                    shared.mydb.commit()

                    response = '%s is neither a valid address nor a redditor' % recipient
                    return [response, 6, amount / 10 ** 30, None, None, None]
        else:
            # a username was specified
            try:
                dummy = getattr(shared.reddit.redditor(recipient), 'is_suspended', False)
                user_or_address = 'user'
            except:
                sql = "UPDATE history SET notes = %s WHERE id = %s"
                val = ('redditor does not exist', entry_id)
                shared.mycursor.execute(sql, val)
                shared.mydb.commit()
                response = "Could not find redditor %s. Make sure you aren't writing or copy/pasting markdown." % recipient
                return [response, 7, amount / 10 ** 30, None, None, None]
    elif parsed_text[0].lower() in shared.donate_commands:
        # if there is no nanocenter name specified, return an error
        if len(parsed_text) < 3:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ("no recipient specified", entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
            response = "You must specify an amount and a NanoCenter project."
            return [response, 5, amount / 10 ** 30, None, None, None]

        sql = "SELECT address FROM projects WHERE project=%s"
        val = (parsed_text[2].lower(), )
        shared.mycursor.execute(sql, val)
        result = shared.mycursor.fetchall()
        # if the nanocenter is found, assign the address, else return an error message
        if len(result) > 0:
            recipient_address = result[0][0]
            user_or_address = 'address'
        else:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ("nanocenter project does not exist", entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
            response = "The NanoCenter project you specified does not exist."
            return [response, 5, amount / 10 ** 30, None, None, None]

        # if the nanocenter address is not valid, return an error message
        if validate_address(address)['valid'] != '1':
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ("nanocenter address invalid", entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
            response = "The Nano address associated with this NanoCenter project is not valid."
            return [response, 6, amount / 10 ** 30, None, None, None]
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
    elif parsed_text[0].lower() in shared.donate_commands:
        print('donate command, setting username to none')
        recipient_username = None
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
    if recipient_username in shared.excluded_redditors:
        response = "Sorry, the redditor '%s' is in the list of excluded addresses. More than likely you didn't intend to send to that user." % (recipient_username)
        return [response, 0, amount / 10 ** 30, recipient_username, recipient_address, None]

    if (user_minimum >= 0) and recipient_address and recipient_username:
        if amount < user_minimum:
            sql = "UPDATE history SET notes = %s WHERE id = %s"
            val = ("below user minimum", entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
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
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()
        print("Sending Nano: ", address, private_key, amount, recipient_address, recipient_username)
        t0 = time.time()
        sent = send(address, private_key, amount, recipient_address)
        print(time.time()-t0)
        sql = "UPDATE history SET hash = %s, return_status = 'cleared' WHERE id = %s"
        val = (sent['hash'], entry_id)
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()

        if comment_or_message == "message" and (not silence):
            message_recipient = str(recipient_username)
            subject = 'You just received a new Nano tip!'
            message_text = shared.new_tip % (
                        amount / 10 ** 30, recipient_address, receiving_new_balance[0] / 10 ** 30,
                        (receiving_new_balance[1] / 10 ** 30 + amount / 10 ** 30), sent['hash']) + shared.comment_footer

            sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
            val = (message_recipient, subject, message_text)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()

        if user_or_address == 'user':
            print('Amount: ', amount / 10 ** 30)
            print('Formatted: %.4f' % (amount / 10 ** 30))
            if silence:
                response = "Sent ```%.4g Nano``` to %s -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (
                       amount / 10 ** 30, recipient_username, sent['hash'])
                return [response, 9, amount / 10 ** 30, recipient_username, recipient_address, sent['hash']]
            else:
                response = "Sent ```%.4g Nano``` to /u/%s -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (
                       amount / 10 ** 30, recipient_username, sent['hash'])
                return [response, 10, amount / 10 ** 30, recipient_username, recipient_address, sent['hash']]
        else:
            response = "Sent ```%.4g Nano``` to [%s](https://nanocrawler.cc/explorer/account/%s) -- " \
                   "[Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (
                   amount / 10 ** 30, recipient_address, recipient_address, sent['hash'])
            return [response, 11, amount / 10 ** 30, recipient_username, recipient_address, sent['hash']]

    elif recipient_address:
        # or if we have an address but no account it might be a nanocenter donation.
        if parsed_text[0].lower() in shared.donate_commands:
            sql = "UPDATE history SET notes = %s, address = %s, username = %s, recipient_address = %s, amount = %s WHERE id = %s"
            val = (
                'sent to nanocenter address', address, username, recipient_address, str(amount), entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
            print("Sending nanocenter address: ", address, private_key, amount, recipient_address)
            sent = send(address, private_key, amount, recipient_address)
            sql = "UPDATE history SET hash = %s, return_status = 'cleared' WHERE id = %s"
            val = (sent['hash'], entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
            response =  "Donated ```%.4g Nano``` to NanoCenter Project [%s](https://nanocrawler.cc/explorer/account/%s). -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (amount/ 10 ** 30, parsed_text[2], recipient_address, sent['hash'])
            return [response, 14, amount / 10 ** 30, parsed_text[2], recipient_address, sent['hash']]

        else:
            sql = "UPDATE history SET notes = %s, address = %s, username = %s, recipient_address = %s, amount = %s WHERE id = %s"
            val = (
                'sent to unregistered address', address, username, recipient_address, str(amount), entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()

            print("Sending Unregistered Address: ", address, private_key, amount, recipient_address)
            sent = send(address, private_key, amount, recipient_address)
            sql = "UPDATE history SET hash = %s, return_status = 'cleared' WHERE id = %s"
            val = (sent['hash'], entry_id)
            shared.mycursor.execute(sql, val)
            shared.mydb.commit()
            response = "Sent ```%.4g Nano``` to [%s](https://nanocrawler.cc/explorer/account/%s). -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (
            amount / 10 ** 30, recipient_address, recipient_address, sent['hash'])
            return [response, 12, amount / 10 ** 30, recipient_username, recipient_address, sent['hash']]

    else:
        # create a new account for redditor
        recipient_address = add_new_account(recipient_username)
        message_recipient = str(recipient_username)
        subject = 'Congrats on receiving your first Nano Tip!'
        message_text = shared.welcome_tipped % (amount/ 10 ** 30, recipient_address, recipient_address) + shared.comment_footer

        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (message_recipient, subject, message_text)
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()
        # x = reddit.redditor(message_recipient).message(subject, message_text)


        sql = "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, recipient_address = %s, amount = %s WHERE id = %s"
        val = ("new user created", address, username, recipient_username, recipient_address,
               str(amount), entry_id)
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()
        sent = send(address, private_key, amount, recipient_address)
        sql = "UPDATE history SET hash = %s, return_status = 'cleared' WHERE id = %s"
        val = (sent['hash'], entry_id)
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()
        print("Sending New Account Address: ", address, private_key, amount, recipient_address, recipient_username)
        response = "Creating a new account for /u/%s and "\
                      "sending ```%.4g Nano```. [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)" % (recipient_username, amount / 10 **30, sent['hash'])
        return [response, 13, amount / 10 ** 30, recipient_username, recipient_address, sent['hash']]


def function_for_test():
    shared.db.commit()