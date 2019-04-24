import shared
import praw
import time
from datetime import datetime
from time import sleep
from rpc_bindings import open_account, generate_account, generate_qr, nano_to_raw, receive_all, send_all, \
    check_balance, validate_address, open_or_receive, get_pendings, open_or_receive_blocks, open_or_receive_block
from rpc_bindings import send_w as send
import mysql.connector
import configparser
import sys
from message_functions import *
from helper_functions import *

# access the sql library
config = configparser.ConfigParser()
config.read('./tipper.ini')

# config.sections()
sql_password = config['SQL']['sql_password']
database_name = config['SQL']['database_name']
tip_bot_on = config['BOT']['tip_bot_on']
tip_bot_username = config['BOT']['tip_bot_username']
program_minimum = float(config['BOT']['program_minimum'])
recipient_minimum = float(config['BOT']['recipient_minimum'])
tip_commands = config['BOT']['tip_commands'].split(',')
tipbot_owner = config['BOT']['tipbot_owner']
cmc_token = config['OTHER']['cmc_token']

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
subreddit = reddit.subreddit(subreddits)

# a few globals. We'll put them in a shared file for use by other scripts
excluded_redditors = ['nano', 'nanos', 'xrb', 'usd', 'eur', 'btc', 'yen']
toggle_receive = True

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
    'balance' or 'address' - Retrieve your account balance. Includes both pocketed and unpocketed transactions
    'minimum <amount>' - (default 0.0001) Sets a minimum amount for receiving tips
    'silence <yes/no>' - (default 'no') Prevents the bot from sending you tip notifications or tagging in posts 
    'history <optional: number of records>' - Retrieves tipbot commands. Default 10, maximum is 50.
    'percentage <percent>' - (default 10 percent) Sets a percentage of returned tips to donate to TipBot development
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

new_tip = """
Somebody just tipped you %s Nano at your address %s. Your new account balance is:\n\n
Available: %s Nano\n\n
Unpocketed: %s Nano\n\n  
Unpocketed Nanos will be pocketed automatically. [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)\n\n
To turn off these notifications, reply with "silence yes".
"""

# make a package with our shared objects. All of these shared variables are static
shared.cmc_token = cmc_token
shared.mycursor = mycursor
shared.mydb = mydb
shared.recipient_minimum = recipient_minimum
shared.welcome_create = welcome_create
shared.tip_bot_username = tip_bot_username
shared.excluded_redditors = excluded_redditors
shared.program_minimum = program_minimum
shared.reddit = reddit
shared.help_text = help_text
shared.new_tip = new_tip
shared.comment_footer = comment_footer
shared.welcome_tipped = welcome_tipped

# this is dynamic
nano_value = {"USD": 0}
shared.nano_value = nano_value


# generator to stream comments and messages to the main loop at the bottom, and contains the auto_receive functionality.
# Maybe this wasn't necessary, but I never get to use generators.
# To check for new messages and comments, the function scans the subreddits and inbox every 6 seconds and builds a
# set of current message. I compare the old set with the new set.
def stream_comments_messages():
    previous_time = time.time()
    previous_comments = {comment for comment in subreddit.comments()}
    previous_messages = {message for message in reddit.inbox.all(limit=25)}
    global toggle_receive
    while True:
        if toggle_receive and tip_bot_on:
            auto_receive()
        toggle_receive = not toggle_receive

        delay = 6-(time.time()-previous_time)

        if delay <= 0:
            delay = 0
        sleep(delay)
        previous_time = time.time()
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
                # if new_comment starts with 't1_, it's just a regular comment'
                if new_comment.name[:3] == 't1_':
                    yield ('comment', new_comment)
        if len(new_messages) >= 1:
            for new_message in new_messages:
                # print(new_message, new_message.subject, new_message.body)
                if new_message.name[:3] == 't4_':
                    yield ('message', new_message)
                # if the message has any of these subjects and it is labeled t1_, it is a username tag
                elif (new_message.subject == "comment reply" or new_message.subject == "username mention" or new_message.subject == "post reply") and new_message.name[:3] == 't1_':
                    # print('****username mention + comment reply')
                    yield ('username mention', new_message)
        else:
            yield None


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
            parsed_text = parse_text(str(message.body[1:]))
        else:
            parsed_text = parse_text(str(message.body))

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

    parsed_text = parse_text(str(message.body))

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


def handle_message(message):
    # activate the account
    activate(message.author)
    response = 'not activated'
    message_body = str(message.body).lower()
    print("Body: **", message_body, "**")
    if message.body[0] == ' ':
        parsed_text = parse_text(str(message.body[1:]))
    else:
        parsed_text = parse_text(str(message.body))
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

    elif parsed_text[0].lower() == 'percentage' or parsed_text[0].lower() == 'percent':
        print("Setting Percentage")
        subject = 'Nano Tipper - Returned Tip Percentage for Donation'
        response = handle_percentage(message)

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
        pass
        #print("receive")
        #subject = 'Nano Tipper - Receive'
        #response = handle_receive(message)
        return None
    elif (parsed_text[0].lower() == 'restart'):
        if str(message.author) == tipbot_owner:
            add_history_record(
                username=str(message.author),
                action='restart',
                comment_text=str(message.body)[:255],
                comment_or_message='message',
                comment_id=message.name,
            )
            sys.exit()

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


def auto_receive():
    count = 0
    mycursor.execute("SELECT username, address, private_key FROM accounts")
    myresult = mycursor.fetchall()

    addresses = [str(result[1]) for result in myresult]
    private_keys = [str(result[2]) for result in myresult]
    mydb.commit()
    pendings = get_pendings(addresses, threshold=nano_to_raw(program_minimum))

    # get any pending blocks from our address
    for address, private_key in zip(addresses, private_keys):
        # allow 5 transactions to be received per cycle. If the bot gets transaction spammed, at least it won't be locked up receiving.
        if count >= 5:
            break
        try:
            if pendings['blocks'][address]:
                for sent_hash in pendings['blocks'][address]:
                    # address, private_key, dictionary where the blocks are the keys
                    open_or_receive_block(address, private_key, sent_hash)
                    count += 1
                    if count >= 2:
                        break

        except KeyError:
            pass
        except Exception as e:
            print(e)


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
                sql = "SELECT address, percentage FROM accounts WHERE username = %s"
                val = (txn[1], )
                mycursor.execute(sql, val)
                returned_results = mycursor.fetchall()
                recipient_address = returned_results[0][0]
                percentage = returned_results[0][1]
                percentage = float(percentage) / 100
                # print('History record: ', txn[0], address, private_key, txn[9], recipient_address)

                # send it back
                donation_amount = int(txn[9])/10**30
                donation_amount = donation_amount * percentage
                donation_amount = nano_to_raw(donation_amount)

                return_amount = int(txn[9]) - donation_amount

                if (return_amount > 0) and (return_amount <= int(txn[9])):
                    hash = send(address, private_key, return_amount, recipient_address)['hash']
                    add_history_record(action='return', hash=hash, amount=return_amount,
                                       notes='Returned transaction from history record %s' % txn[0])
                if (donation_amount > 0) and (donation_amount <= int(txn[9])):
                    hash2 = send(address, private_key, donation_amount, 'xrb_3jy9954gncxbhuieujc3pg5t1h36e7tyqfapw1y6zukn9y1g6dj5xr7r6pij')['hash']
                    add_history_record(action='donate', hash=hash2, amount=donation_amount,
                                       notes='Donation from returned tip %s' % txn[0])
                # print("Returning a transaction. ", hash)

                # update database if everything goes through
                sql = "UPDATE history SET return_status = 'returned' WHERE id = %s"
                val = (txn[0], )
                mycursor.execute(sql, val)
                mydb.commit()

                # send a message informing the tipper that the tip is being returned
                message_recipient = txn[1]
                subject = 'Returned your tip of %s to %s' % (int(txn[9])/10**30, result)
                message_text = "Your tip to %s for %s Nano was returned since the user never activated their account, and %s percent of this was donated to the TipBot development fund. You can change this percentage by messaging the TipBot 'percentage <amount>', where <amount> is a number between 0 and 100." % (result, int(txn[9])/10**30, round(percentage*100, 2))
                sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
                val = (message_recipient, subject, message_text)
                mycursor.execute(sql, val)
                mydb.commit()

# main loop
t0 = time.time()
check_inactive_transactions()
for action_item in stream_comments_messages():
    # our 'stream_comments_messages()' generator will give us either messages or
    # (t1 = comment, t4 = message)
    # The bot handles these differently
    if action_item is None:
        pass
    elif message_in_database(action_item[1]):
        # print("Previous message was found in stream...")
        # print('Previous: ', action_item[1].author, ' - ', action_item[1].name, ' - ', action_item[1].body[:25])
        pass

    elif action_item[0] == 'comment':
        if action_item[1].body[0] == ' ':
            # remove any leading spaces. for convenience
            parsed_text = parse_text(str(action_item[1].body[1:]))
            #parsed_text = str(action_item[1].body[1:]).lower().replace('\\', '').replace('\n', ' ').split(' ')
        else:
            parsed_text = parse_text(str(action_item[1].body))
            #parsed_text = str(action_item[1].body).lower().replace('\\', '').replace('\n', ' ').split(' ')
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
            parsed_text = parse_text(str(action_item[1].body[1:]))
        else:
            parsed_text = parse_text(str(action_item[1].body))


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

    # run the inactive script at the end of the loop; every 12 hours
    if time.time()-t0 > 43200:
        t0 = time.time()
        check_inactive_transactions()


