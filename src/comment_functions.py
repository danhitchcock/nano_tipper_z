import datetime
import text
from shared import (
    TIP_COMMANDS,
    PROGRAM_MINIMUM,
    LOGGER,
    TIP_BOT_USERNAME,
    from_raw,
    to_raw,
    Message,
    Subreddit,
    History,
    NumberUtil
)
from tipper_functions import (
    add_history_record,
    parse_text,
    update_history_notes,
    TipError,
    parse_raw_amount,
    send_pm,
    check_balance,
)
from tipper_rpc import send
import tipper_functions

# handles tip commands on subreddits
def handle_comment(message):

    response = send_from_comment(message)
    response_text = text.make_response_text(message, response)

    # check if subreddit is untracked or silent. If so, PM the users.
    if response["subreddit_status"] in ["silent", "hostile"]:
        message_recipient = str(message.author)
        if response["status"] < 100:
            subject = text.SUBJECTS["success"]
        else:
            subject = text.SUBJECTS["failure"]
        message_text = response_text + text.COMMENT_FOOTER
        msg = Message(
            username=message_recipient,
            subject=subject,
            message=message_text
        )
        msg.save()
    else:
        message.reply(response_text + text.COMMENT_FOOTER)


def send_from_comment(message):
    """
    Error codes:
    Success
    10 - sent to existing user
    20 - sent to new user
    30 - sent to address
    40 - donated to nanocenter project
    Tip not sent
    100 - sender account does not exist
    110 - Amount and/or recipient not specified
    120 - could not parse send amount
    130 - below program minimum
    150 - below 1 nano for untracked sub
    160 - insufficient funds
    170 - invalid address / recipient
    180 - below recipient minimum
    200 - No Nanocenter Project specified
    210 - Nanocenter Project does not exist



    Extracts send command information from a PM command
    :param message:
    :return: response string
    """

    parsed_text = parse_text(str(message.body))
    response = {"username": str(message.author)}
    message_time = datetime.datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    entry_id = add_history_record(
        username=response["username"],
        action="send",
        comment_or_message="comment",
        comment_id=message.name,
        reddit_time=message_time,
        comment_text=str(message.body)[:255],
    )

    # don't do anything if the first word is a tip command or username
    if (parsed_text[0] in [f"/u/{TIP_BOT_USERNAME}", f"u/{TIP_BOT_USERNAME}"]) or (
        parsed_text[0] in TIP_COMMANDS
    ):
        pass
    # if the second to last is a username or tip command, redifine parsed text
    elif (parsed_text[-2] in [f"/u/{TIP_BOT_USERNAME}", f"u/{TIP_BOT_USERNAME}"]) or (
        parsed_text[-2] in TIP_COMMANDS
    ):
        parsed_text = parsed_text[-2:]

    # before we can do anything, check the subreddit status for generating the response
    response["subreddit"] = str(message.subreddit).lower()
    try:
        sr = Subreddit.select(Subreddit.status, Subreddit.minimum).where(Subreddit.subreddit == response["subreddit"]).get()
        response["subreddit_status"] = sr.status
        response["subreddit_minimum"] = sr.minimum            
    except Subreddit.DoesNotExist:
        response["subreddit_status"] = "untracked"
        response["subreddit_minimum"] = "1"        

    if parsed_text[0] in TIP_COMMANDS and len(parsed_text) <= 1:
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

    # check that it's above the subreddit minimum
    if response["amount"] < to_raw(response["subreddit_minimum"]):
        update_history_notes(entry_id, "amount below subreddit minimum")
        response["status"] = 150
        return response

    # if it's a normal send, pull the account author
    # we will distinguish users from donations by the presence of a private key
    if parsed_text[0] in (
        TIP_COMMANDS + [f"/u/{TIP_BOT_USERNAME}", f"u/{TIP_BOT_USERNAME}"]
    ):

        response["status"] = 10
        response["recipient"] = str(message.parent().author)
        recipient_info = tipper_functions.account_info(response["recipient"])
        if not recipient_info:
            response["status"] = 20
            recipient_info = tipper_functions.add_new_account(response["recipient"])
            if recipient_info is None:
                return text.TIP_CREATE_ACCT_ERROR
        elif recipient_info["silence"]:
            response["status"] = 11
        elif not recipient_info["opt_in"]:
            response["status"] = 190
            return response
    else:
        response["status"] = 999
        return response

    if sender_info["address"] == recipient_info["address"]:
        # Don't allow sends to yourself
        response["status"] = 200
        return response

    # send the bans!!
    response["hash"] = send(
        sender_info["address"],
        response["amount"],
        recipient_info["address"],
    )["block"]

    # Update the sql and send the PMs
    History.update(
        notes = "sent to user",
        address = sender_info["address"],
        username = sender_info["username"],
        recipient_username = recipient_info["username"],
        recipient_address = recipient_info["address"],
        amount = str(response["amount"]),
        hash = response["hash"],
        return_status = "cleared"
    ).where(History.id == entry_id).execute()
    
    LOGGER.info(
        f"Sending Banano: {sender_info['address']} {sender_info['private_key']} {response['amount']} {recipient_info['address']} {recipient_info['username']}"
    )

    if response["status"] == 20:
        subject = text.SUBJECTS["first_tip"]
        message_text = (
            text.WELCOME_TIP
            % (
                NumberUtil.format_float(from_raw(response["amount"])),
                recipient_info["address"],
                recipient_info["address"],
            )
            + text.COMMENT_FOOTER
        )
        send_pm(recipient_info["username"], subject, message_text)
        return response
    else:
        if not recipient_info["silence"]:
            receiving_new_balance = check_balance(recipient_info["address"])
            subject = text.SUBJECTS["new_tip"]
            message_text = (
                text.NEW_TIP
                % (
                    NumberUtil.format_float(from_raw(response["amount"])),
                    recipient_info["address"],
                    from_raw(receiving_new_balance),
                    response["hash"],
                )
                + text.COMMENT_FOOTER
            )
            send_pm(recipient_info["username"], subject, message_text)
        return response
