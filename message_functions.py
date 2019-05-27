from datetime import datetime
from helper_functions import parse_text, add_history_record, add_new_account, handle_send_nano
from rpc_bindings import check_balance, open_or_receive, nano_to_raw
import shared


def handle_percentage(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    # user may select a minimum tip amount to avoid spamming. Tipbot minimum is 0.001
    username = str(message.author)
    # find any accounts associated with the redditor
    parsed_text = parse_text(str(message.body))

    # there should be at least 2 words, a minimum and an amount.
    if len(parsed_text) < 2:
        response = "I couldn't parse your command. I was expecting 'percentage <amount>'. Be sure to check your spacing."
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
    if round(amount, 2) < 0:
        response = "Did not update. Your percentage cannot be negative."
        return response

    if round(amount, 2) > 100:
        response = "Did not update. Your percentage must be 100 or lower."
        return response

    # check if the user is in the database
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username, )
    shared.mycursor.execute(sql, val)
    result = shared.mycursor.fetchall()
    if len(result) > 0:
        #open_or_receive(result[0][0], result[0][1])
        #balance = check_balance(result[0][0])
        add_history_record(
            username=username,
            action='percentage',
            amount=round(amount, 2),
            address=result[0][0],
            comment_or_message='message',
            comment_id=message.name,
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            comment_text=str(message.body)[:255]
        )
        sql = "UPDATE accounts SET percentage = %s WHERE username = %s"
        val = (round(amount, 2), username)
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()
        response = "Updating donation percentage to %s"%round(amount, 2)
        return response
    else:
        add_history_record(
            username=username,
            action='percentage',
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            amount=round(amount, 2),
            comment_id=message.name,
            comment_text=str(message.body)[:255]
        )
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
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
    shared.mycursor.execute(sql, val)
    result = shared.mycursor.fetchall()
    if len(result) > 0:
        results = check_balance(result[0][0])

        response = "At address %s:\n\nAvailable: %s Nano\n\nUnpocketed: %s Nano\n\nNano will be pocketed automatically unless the transaction is below 0.0001 Nano." \
                   "\n\nhttps://nanocrawler.cc/explorer/account/%s" % (result[0][0], results[0]/10**30, results[1]/10**30, result[0][0])

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
    shared.mycursor.execute(sql, val)
    result = shared.mycursor.fetchall()
    if len(result) is 0:
        address = add_new_account(username)
        response = shared.welcome_create % (address, address)
        message_recipient = shared.tip_bot_username
        subject = 'send'
        message_text = 'send 0.001 %s' % username
        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (message_recipient, subject, message_text)
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()

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
    response = shared.help_text
    return response


def handle_history(message):
    message_time = datetime.utcfromtimestamp(message.created_utc)  # time the reddit message was created
    username = str(message.author)
    parsed_text = parse_text(str(message.body))
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
    shared.mycursor.execute(sql, val)
    result = shared.mycursor.fetchall()
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
        shared.mycursor.execute(sql, val)
        results = shared.mycursor.fetchall()
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
    parsed_text = parse_text(str(message.body))

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
    if nano_to_raw(amount) < nano_to_raw(shared.program_minimum):
        response = "Did not update. The amount you specified is below the program minimum of %s Nano."%shared.program_minimum
        return response

    # check if the user is in the database
    sql = "SELECT address FROM accounts WHERE username=%s"
    val = (username, )
    shared.mycursor.execute(sql, val)
    result = shared.mycursor.fetchall()
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
        shared.mycursor.execute(sql, val)
        shared.mydb.commit()
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
    shared.mycursor.execute(sql, val)
    result = shared.mycursor.fetchall()
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
        return response
    else:
        add_history_record(
            username=username,
            action='receive',
            reddit_time=message_time.strftime('%Y-%m-%d %H:%M:%S'),
            comment_id=message.name,
            comment_or_message='message'
        )
        response = "You do not currently have an account open. To create one, respond with the text 'create' in the message body."
        return response


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

    parsed_text = parse_text(str(message.body))

    if len(parsed_text) < 2:
        response = "I couldn't parse your command. I was expecting 'silence <yes/no>'. Be sure to check your spacing."
        return response

    if parsed_text[1] == 'yes':
        sql = "UPDATE accounts SET silence = TRUE WHERE username = %s "
        val = (username, )
        shared.mycursor.execute(sql, val)
        response = "Silence set to 'yes'. You will no longer receive tip notifications or be tagged by the bot."
    elif parsed_text[1] == 'no':
        sql = "UPDATE accounts SET silence = FALSE WHERE username = %s"
        val = (username, )
        shared.mycursor.execute(sql, val)
        response = "Silence set to 'no'. You will receive tip notifications and be tagged by the bot in replies."
    else:
        response = "I did not see 'no' or 'yes' after 'silence'. If you did type that, check your spacing."
    shared.mydb.commit()

    return response


def handle_send(message):
    """
    Extracts send command information from a PM command
    :param message:
    :return:
    """
    parsed_text = parse_text(str(message.body))
    response = handle_send_nano(message, parsed_text, 'message')
    response = response[0]
    return response