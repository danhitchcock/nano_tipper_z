import sys
from datetime import datetime
import tipper_functions
import text
from tipper_functions import (
    parse_text,
    add_history_record,
    TipError,
    update_history_notes,
    parse_raw_amount,
    send_pm,
    activate,
)
from tipper_rpc import (
    check_balance,
    validate_address,
    send,
)
from text import WELCOME_CREATE, WELCOME_TIP, COMMENT_FOOTER, NEW_TIP
import shared
from shared import (
    PROGRAM_MINIMUM,
    REDDIT,
    LOGGER,
    TIPBOT_OWNER,
    to_raw,
    from_raw,
    Account,
    History,
    Subreddit
)


def handle_message(message):
    response = "not activated"
    parsed_text = parse_text(str(message.body))
    command = parsed_text[0].lower()
    # only activate if it's not an opt-out command
    if command != "opt-out":
        activate(message.author)

    # normal commands
    if command in ["help", "!help"]:
        LOGGER.info("Helping")
        subject = text.SUBJECTS["help"]
        response = handle_help(message)
    elif command in ["balance", "address"]:
        LOGGER.info("balance")
        subject = text.SUBJECTS["balance"]
        response = handle_balance(message)
    elif command == "minimum":
        LOGGER.info("Setting Minimum")
        subject = text.SUBJECTS["minimum"]
        response = handle_minimum(message)
    elif command in ["create", "register"]:
        LOGGER.info("Creating")
        subject = text.SUBJECTS["create"]
        response = handle_create(message)
    elif command in ["send", "withdraw"]:
        subject = text.SUBJECTS["send"]
        LOGGER.info("send via PM")
        response = handle_send(message)
        response = text.make_response_text(message, response)
    elif command == "history":
        LOGGER.info("history")
        subject = text.SUBJECTS["history"]
        response = handle_history(message)
    elif command == "silence":
        LOGGER.info("silencing")
        subject = text.SUBJECTS["silence"]
        response = handle_silence(message)
    elif command == "subreddit":
        LOGGER.info("subredditing")
        subject = text.SUBJECTS["subreddit"]
        response = handle_subreddit(message)
    elif command == "opt-out":
        LOGGER.info("opting out")
        response = handle_opt_out(message)
        subject = text.SUBJECTS["opt-out"]
    elif command == "opt-in":
        LOGGER.info("opting in")
        subject = text.SUBJECTS["opt-in"]
        response = handle_opt_in(message)
    # a few administrative tasks
    elif command in ["restart", "stop", "disable", "deactivate"]:
        if str(message.author).lower() in [
            TIPBOT_OWNER,
        ]:  # "joohansson"]:
            add_history_record(
                username=str(message.author),
                action="restart",
                comment_text=str(message.body)[:255],
                comment_or_message="message",
                comment_id=message.name,
            )
            sys.exit()
    else:
        add_history_record(
            username=str(message.author),
            comment_text=str(message.body)[:255],
            comment_or_message="message",
            comment_id=message.name,
        )
        return None
    message_recipient = str(message.author)
    message_text = response + COMMENT_FOOTER
    send_pm(message_recipient, subject, message_text, bypass_opt_out=True)

def handle_balance(message):
    username = str(message.author)
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message="message",
        reddit_time=message_time,
        action="balance",
        comment_id=message.name,
        comment_text=str(message.body)[:255],
    )
    try:
        acct = Account.get(username=username)
        results = check_balance(acct.address)

        response = text.BALANCE % (
            acct.address,
            from_raw(results[0]),
            from_raw(results[1]),
            acct.address,
        )

        return response        
    except Account.DoesNotExist:
        return text.NOT_OPEN

def handle_create(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        comment_or_message="message",
        reddit_time=message_time,
        action="create",
        comment_id=message.name,
        comment_text=str(message.body)[:255],
    )

    username = str(message.author)
    try:
        acct = Account.get(username=username)
        response = text.ALREADY_EXISTS % (acct.address, acct.address)
    except Account.DoesNotExist:
        address = tipper_functions.add_new_account(username)
        if address is None:
            response = text.ACCOUNT_MAKE_ERROR_ERROR
        else:
            response = WELCOME_CREATE % (address, address)
        # reddit.redditor(message_recipient).message(subject, message_text)

    return response


def handle_help(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    add_history_record(
        username=str(message.author),
        action="help",
        comment_or_message="message",
        comment_id=message.name,
        reddit_time=message_time,
    )
    response = text.HELP
    return response


def handle_history(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    username = str(message.author)
    parsed_text = parse_text(str(message.body))
    num_records = 10
    # if there are more than 2 words, one of the words is a number for the number of records
    if len(parsed_text) >= 2:
        if parsed_text[1].lower() == "nan" or ("inf" in parsed_text[1].lower()):
            response = text.NAN
            return response
        try:
            num_records = int(parsed_text[1])
        except:
            response = text.NAN
            return response

    # check that it's greater than 50
    if num_records > 50:
        num_records = 50

    # check if the user is in the database
    try:
        acct = Account.get(username=username)
        # open_or_receive(result[0][0], result[0][1])
        # balance = check_balance(result[0][0])
        add_history_record(
            username=username,
            action="history",
            amount=num_records,
            address=acct.address,
            comment_or_message="message",
            comment_id=message.name,
            reddit_time=message_time,
            comment_text=str(message.body)[:255],
        )
        response = "Here are your last %s historical records:\n\n" % num_records
        history = History.select(History.reddit_time, History.action, History.amount,
                    History.comment_id, History.notes, History.recipient_username,
                    History.recipient_address).where(History.username == username).order_by(History.id.desc())
        for result in history:
            try:
                amount = result.amount
                if (result.action == "send") and amount:
                    amount = from_raw(int(result.amount))
                    if (
                        result.notes == "sent to registered redditor"
                        or result.notes == "new user created"
                    ):
                        response += (
                            "%s: %s | %s Nano to %s | reddit object: %s | %s\n\n"
                            % (
                                result.reddit_time.strftime("%Y-%m-%d %H:%M:%S"),
                                result.action,
                                amount,
                                result.recipient_username,
                                result.comment_id,
                                result.notes,
                            )
                        )
                    elif (
                        result.notes == "sent to registered address"
                        or result.notes == "sent to unregistered address"
                    ):
                        response += (
                            "%s: %s | %s Nano to %s | reddit object: %s | %s\n\n"
                            % (
                                result.reddit_time.strftime("%Y-%m-%d %H:%M:%S"),
                                result.action,
                                amount,
                                result.recipient_address,
                                result.comment_id,
                                result.notes,
                            )
                        )
                elif result.action == "send":
                    response += "%s: %s | reddit object: %s | %s\n\n" % (
                        result.reddit_time.strftime("%Y-%m-%d %H:%M:%S"),
                        result.action,
                        result.comment_id,
                        result.notes,
                    )
                elif (result.action == "minimum") and amount:
                    amount = from_raw(int(result[2]))
                    response += "%s: %s | %s | %s | %s\n\n" % (
                        result.reddit_time.strftime("%Y-%m-%d %H:%M:%S"),
                        result.action,
                        amount,
                        result.comment_id,
                        result.notes,
                    )
                else:
                    response += "%s: %s | %s | %s | %s\n\n" % (
                        result.reddit_time.strftime("%Y-%m-%d %H:%M:%S"),
                        result.action,
                        amount,
                        result.comment_id,
                        result.notes,
                    )
            except:
                response += (
                    "Unparsed Record: Nothing is wrong, I just didn't "
                    "parse this record properly.\n\n"
                )

        return response        
    except Account.DoesNotExist:
        add_history_record(
            username=username,
            action="history",
            reddit_time=message_time,
            amount=num_records,
            comment_id=message.name,
            comment_text=str(message.body)[:255],
        )
        response = text.NOT_OPEN
        return response


def handle_minimum(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    # user may select a minimum tip amount to avoid spamming. Tipbot minimum is 0.001
    username = str(message.author)
    # find any accounts associated with the redditor
    parsed_text = parse_text(str(message.body))

    # there should be at least 2 words, a minimum and an amount.
    if len(parsed_text) < 2:
        response = text.MINIMUM["parse_error"]
        return response
    # check that the minimum is a number

    if parsed_text[1].lower() == "nan" or ("inf" in parsed_text[1].lower()):
        response = text.NAN
        return response
    try:
        amount = float(parsed_text[1])
    except:
        response = text.NAN % parsed_text[1]
        return response

    # check that it's greater than 0.01
    if to_raw(amount) < to_raw(PROGRAM_MINIMUM):
        response = text.MINIMUM["below_program"] % PROGRAM_MINIMUM
        return response

    # check if the user is in the database
    try:
        acct = Account.get(username=username)
        # open_or_receive(result[0][0], result[0][1])
        # balance = check_balance(result[0][0])
        add_history_record(
            username=username,
            action="minimum",
            amount=to_raw(amount),
            address=acct.address,
            comment_or_message="message",
            comment_id=message.name,
            reddit_time=message_time,
            comment_text=str(message.body)[:255],
        )
        Account.update(minimum=str(to_raw(amount))).where(Account.username == username).execute()
        response = text.MINIMUM["set_min"] % amount
        return response        
    except Account.DoesNotExist:
        add_history_record(
            username=username,
            action="minimum",
            reddit_time=message_time,
            amount=to_raw(amount),
            comment_id=message.name,
            comment_text=str(message.body)[:255],
        )
        response = text.NOT_OPEN
        return response


def handle_silence(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    username = str(message.author)
    add_history_record(
        username=str(message.author),
        action="silence",
        comment_or_message="message",
        comment_id=message.name,
        reddit_time=message_time,
    )

    parsed_text = parse_text(str(message.body))

    if len(parsed_text) < 2:
        response = text.SILENCE["parse_error"]
        return response

    if parsed_text[1] == "yes":
        Account.update(silence=True).where(Account.username == username).execute()
        response = text.SILENCE["yes"]
    elif parsed_text[1] == "no":
        Account.update(silence=False).where(Account.username == username).execute()
        response = text.SILENCE["no"]
    else:
        response = text.SILENCE["yes_no"]

    return response


def handle_subreddit(message):
    parsed_text = parse_text(str(message.body))
    # If it is just the subreddit, return all the subreddits
    if len(parsed_text) < 2:
        response = text.SUBREDDIT["all"]
        subreddits = Subreddit.select(Subreddit.subreddit, Subreddit.status, Subreddit.minimum)
        for result in subreddits:
            result = [str(i) for i in result]
            response += f"{result.subreddit}, {result.status}, {result.minimum}"
            response += "\n\n"
        return response

    # Return the subreddit stats
    if len(parsed_text) < 3:
        response = text.SUBREDDIT["one"]
        try:
            result = Subreddit.select(Subreddit.subreddit, Subreddit.status, Subreddit.minimum).where(Subreddit.subreddit == parsed_text[1]).get()
            response += f"{result.subreddit}, {result.status}, {result.minimum}"
        except Subreddit.DoesNotExist:
            pass
        return response % parsed_text[1]

    # check if the user is a moderator of the subreddit
    if message.author not in REDDIT.subreddit(parsed_text[1]).moderator():
        return text.SUBREDDIT["not_mod"] % parsed_text[1]

    # change the subreddit minimum
    if parsed_text[2] in ["minimum", "min"]:
        try:
            float(parsed_text[3])
        except:
            return text.NAN % parsed_text[3]
        Subreddit.update(minimum=parsed_text[3]).where(Subreddit.subreddit == parsed_text[1]).execute()

        return text.SUBREDDIT["minimum"] % (parsed_text[1], parsed_text[3])

    if parsed_text[2] in ("disable", "deactivate"):
        # disable the bot
        try:
            Subreddit.delete().where(Subreddit.subreddit == parsed_text[1]).execute()
        except:
            pass
        return text.SUBREDDIT["deactivate"] % parsed_text[1]

    if parsed_text[2] in ("enable", "activate"):
        # if it's at least 4 words, set the status to that one
        if (len(parsed_text) > 3) and (parsed_text[3] in ["full", "minimal", "silent"]):
            status = parsed_text[3]
        else:
            status = "full"
        # sql to change subreddit to that status
        try:
            subreddit = Subreddit.get(subreddit=parsed_text[1])
            Subreddit.update(status=status).where(Subreddit.subreddit == parsed_text[1]).execute()
        except Subreddit.DoesNotExist:
            subreddit = Subreddit(
                subreddit=parsed_text[1],
                reply_to_comments=True,
                footer=None,
                status=status
            )
            await subreddit.save(force_insert=True)        
        return text.SUBREDDIT["activate"] % status

    # only 4 word commands after this point
    if len(parsed_text) < 4:
        return text.SUBREDDIT["error"]


def handle_send(message):
    """
    Extracts send command information from a PM command
    :param message:
    :return:
    """
    parsed_text = parse_text(str(message.body))
    username = str(message.author)
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    entry_id = add_history_record(
        username=username,
        action="send",
        comment_or_message="message",
        comment_id=message.name,
        reddit_time=message_time,
        comment_text=str(message.body)[:255],
    )
    response = {"username": username}

    # check that there are enough fields (i.e. a username)
    if len(parsed_text) <= 2:
        update_history_notes(entry_id, "no recipient or amount specified")
        response["status"] = 110
        return response

    # pull sender account info
    sender_info = tipper_functions.account_info(response["username"])
    if not sender_info:
        update_history_notes(entry_id, "user does not exist")
        response["status"] = 100
        return response

    # parse the amount
    try:
        response["amount"] = parse_raw_amount(parsed_text, response["username"])
    except TipError as err:
        response["status"] = 120
        response["amount"] = parsed_text[1]
        update_history_notes(entry_id, err.sql_text)
        return response

    # check if it's above the program minimum
    if response["amount"] < to_raw(PROGRAM_MINIMUM):
        update_history_notes(entry_id, "amount below program limit")
        response["status"] = 130
        return response

    # check the user's balance
    if response["amount"] > sender_info["balance"]:
        update_history_notes(entry_id, "insufficient funds")
        response["status"] = 160
        return response

    recipient_text = parsed_text[2]

    # catch invalid redditor AND address
    try:
        recipient_info = parse_recipient_username(recipient_text)
    except TipError as err:
        update_history_notes(entry_id, err.sql_text)
        response["recipient"] = recipient_text
        response["status"] = 170
        return response

    # if we have a username, pull their info
    if "username" in recipient_info.keys():
        response["recipient"] = recipient_info["username"]
        recipient_name = recipient_info["username"]
        recipient_info = tipper_functions.account_info(recipient_name)
        response["status"] = 10
        if recipient_info is None:
            recipient_info = tipper_functions.add_new_account(response["recipient"])
            if recipient_info is None:
                return text.TIP_CREATE_ACCT_ERROR
            response["status"] = 20
        elif not recipient_info["opt_in"]:
            response["status"] = 190
            return response
    # check if it's an address
    else:
        # otherwise, just use the address. Everything is None except address
        recipient_info["minimum"] = 0
        response["recipient"] = recipient_info["address"]
        response["status"] = 30

    # check the send amount is above the user minimum, if a username is provided
    # if it was just an address, this would be -1
    if response["amount"] < recipient_info["minimum"]:
        update_history_notes(entry_id, "below user minimum")
        response["status"] = 180
        response["minimum"] = recipient_info["minimum"]
        return response

    response["hash"] = send(
        sender_info["address"],
        response["amount"],
        recipient_info["address"],
    )["block"]
    # if it was an address, just send to the address
    if "username" not in recipient_info.keys():
        History.update(notes="send to address", address=sender_info["address"], username=sender_info["username"], recipient_username=None, recipient_address=recipient_info["address"],
                    amount=str(response["amount"]), return_status="cleared").where(History.id == entry_id).execute()
        LOGGER.info(
            f"Sending Nano: {sender_info['address']} {sender_info['private_key']} {response['amount']} {recipient_info['address']}"
        )
        return response

    # Update the sql and send the PMs
    History.update(notes="send to address", address=sender_info["address"], username=sender_info["username"], recipient_username=recipient_info["username"], recipient_address=recipient_info["address"],
                amount=str(response["amount"]), return_status="cleared").where(History.id == entry_id).execute()
    LOGGER.info(
        f"Sending Nano: {sender_info['address']} {sender_info['private_key']} {response['amount']} {recipient_info['address']} {recipient_info['username']}"
    )

    if response["status"] == 20:
        subject = text.SUBJECTS["first_tip"]
        message_text = (
            WELCOME_TIP
            % (
                from_raw(response["amount"]),
                recipient_info["address"],
                recipient_info["address"],
            )
            + COMMENT_FOOTER
        )
        send_pm(recipient_info["username"], subject, message_text)
        return response
    else:
        if not recipient_info["silence"]:
            receiving_new_balance = check_balance(recipient_info["address"])
            subject = text.SUBJECTS["new_tip"]
            message_text = (
                NEW_TIP
                % (
                    from_raw(response["amount"]),
                    recipient_info["address"],
                    from_raw(receiving_new_balance[0]),
                    from_raw(receiving_new_balance[1]),
                    response["hash"],
                )
                + COMMENT_FOOTER
            )
            send_pm(recipient_info["username"], subject, message_text)
        return response


def handle_opt_out(message):
    add_history_record(
        username=str(message.author),
        action="opt-out",
        comment_or_message="message",
        comment_id=message.name,
        reddit_time=datetime.utcfromtimestamp(message.created_utc),
    )

    Account.update(opt_in=False).where(Account.username == str(message.author)).execute()

    response = text.OPT_OUT
    return response


def handle_opt_in(message):
    add_history_record(
        username=str(message.author),
        action="opt-in",
        comment_or_message="message",
        comment_id=message.name,
        reddit_time=datetime.utcfromtimestamp(message.created_utc),
    )
    Account.update(opt_in=True).where(Account.username == str(message.author)).execute()
    response = text.OPT_IN
    return response

def parse_recipient_username(recipient_text):
    """
    Determines if a specified recipient is a nano address or a redditor
    :param recipient_text:
    :return: either {address: valid_address} or {username: user}
    """
    # remove the /u/ or u/
    if recipient_text[:3].lower() == "/u/":
        recipient_text = recipient_text[3:]
    elif recipient_text[:2].lower() == "u/":
        recipient_text = recipient_text[2:]

    if (
        shared.CURRENCY == "Nano"
        and (
            recipient_text[:5].lower() == "nano_"
            or recipient_text[:4].lower() == "xrb_"
        )
        or (shared.CURRENCY == "Banano" and recipient_text[:4].lower() == "ban_")
    ):
        # check valid address
        success = validate_address(recipient_text)
        if success["valid"] == "1":
            return {"address": recipient_text}
        # if not, check if it is a redditor disguised as an address (e.g.
        # nano_is_awesome, nano_tipper_z)
        else:
            try:
                _ = getattr(REDDIT.redditor(recipient_text), "is_suspended", False)
                return {"username": recipient_text}
            except:
                raise TipError(
                    "invalid address or address-like redditor does not exist",
                    "%s is neither a valid address nor a redditor" % recipient_text,
                )
    else:
        # a username was specified
        try:
            _ = getattr(REDDIT.redditor(recipient_text), "is_suspended", False)
            return {"username": recipient_text}
        except:
            raise TipError(
                "redditor does not exist",
                "Could not find redditor %s. Make sure you aren't writing or "
                "copy/pasting markdown." % recipient_text,
            )
