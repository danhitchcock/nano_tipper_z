import datetime
import text
from shared import (
    MYDB,
    MYCURSOR,
    DONATE_COMMANDS,
    TIP_COMMANDS,
    PROGRAM_MINIMUM,
    LOGGER,
    TIP_BOT_USERNAME,
    EXCLUDED_REDDITORS,
)
from tipper_functions import (
    nano_to_raw,
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
            subject = "Your Tip Was Successful"
        else:
            subject = "You Tip Did Not Go Through"
        message_text = response_text + text.COMMENT_FOOTER
        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (message_recipient, subject, message_text)
        MYCURSOR.execute(sql, val)
        MYDB.commit()
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
    140 - currency code issue
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
        reddit_time=message_time.strftime("%Y-%m-%d %H:%M:%S"),
        comment_text=str(message.body)[:255],
    )

    # check if it's a donate command at the end
    if parsed_text[-3] in DONATE_COMMANDS:
        parsed_text = parsed_text[-3:]
    # check if it's a send command at the end
    if parsed_text[-2] in TIP_COMMANDS:
        parsed_text = parsed_text[-2:]

    # before we can do anything, check the subreddit status for generating the response
    # check if amount is above subreddit minimum.
    response["subreddit"] = str(message.subreddit).lower()
    sql = "SELECT status FROM subreddits WHERE subreddit=%s"
    val = (response["subreddit"],)
    results = tipper_functions.query_sql(sql, val)
    if len(results) == 0:
        response["subreddit_minimum"] = 1
        results = [["untracked"]]
    elif results[0][0] in ["full", "friendly", "minimal", "silent"]:
        response["subreddit_minimum"] = 0
    else:
        response["subreddit_minimum"] = 1
    response["subreddit_status"] = results[0][0]

    # check that it wasn't a mistyped currency code or something
    if parsed_text[2] in EXCLUDED_REDDITORS:
        response["status"] = 140
        return response

    if parsed_text[0] in TIP_COMMANDS and len(parsed_text) <= 1:
        update_history_notes(entry_id, "no recipient or amount specified")
        response["status"] = 110
        return response

    if parsed_text[0] in DONATE_COMMANDS and len(parsed_text) <= 2:
        response["status"] = 110
        update_history_notes(entry_id, "no recipient or amount specified")
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
    if response["amount"] < nano_to_raw(PROGRAM_MINIMUM):
        update_history_notes(entry_id, "amount below program limit")
        response["status"] = 130
        return response

    # check the user's balance
    if response["amount"] > sender_info["balance"]:
        update_history_notes(entry_id, "insufficient funds")
        response["status"] = 160
        return response

    if response["amount"] < nano_to_raw(response["subreddit_minimum"]):
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
        elif recipient_info["silence"]:
            response["status"] = 11

    elif parsed_text[0] in DONATE_COMMANDS:
        response["recipient"] = parsed_text[2]
        results = tipper_functions.query_sql(
            "FROM projects SELECT address WHERE project = %s", (parsed_text[2],)
        )
        if len(results) <= 0:
            response["status"] = 210
            return response

        recipient_info = {
            "username": parsed_text[2],
            "address": results[0][0],
            "minimum": -1,
        }
        response["status"] = 40
    else:
        response["status"] = 999
        return response

    # check the send amount is above the user minimum, if a username is provided
    # if it was just an address, this would be -1
    if response["amount"] < recipient_info["minimum"]:
        update_history_notes(entry_id, "below user minimum")
        response["status"] = 180
        response["minimum"] = recipient_info["minimum"]
        return response

    # send the nanos!!
    response["hash"] = send(
        sender_info["address"],
        sender_info["private_key"],
        response["amount"],
        recipient_info["address"],
    )["hash"]

    # Update the sql and send the PMs
    sql = (
        "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, "
        "recipient_address = %s, amount = %s, return_status = %s WHERE id = %s"
    )
    val = (
        "sent to user",
        sender_info["address"],
        sender_info["username"],
        recipient_info["username"],
        recipient_info["address"],
        str(response["amount"]),
        "cleared",
        entry_id,
    )
    tipper_functions.exec_sql(sql, val)
    LOGGER.info(
        f"Sending Nano: {sender_info['address']} {sender_info['private_key']} {response['amount']} {recipient_info['address']} {recipient_info['username']}"
    )

    # Update the sql and send the PMs if needed
    # if there is no private key, it's a donation. No PMs to send
    if "private_key" not in recipient_info.keys():
        sql = "UPDATE history SET notes = %s, address = %s, username = %s, recipient_address = %s, amount = %s WHERE id = %s"
        val = (
            "sent to nanocenter address",
            sender_info["address"],
            sender_info["username"],
            recipient_info["address"],
            str(response["amount"]),
            entry_id,
        )
        tipper_functions.exec_sql(sql, val)
        response["status"] = 40
        return response

    # update the sql database and send
    sql = (
        "UPDATE history SET notes = %s, address = %s, username = %s, recipient_username = %s, "
        "recipient_address = %s, amount = %s, return_status = %s WHERE id = %s"
    )
    val = (
        "sent to user",
        recipient_info["address"],
        recipient_info["username"],
        recipient_info["username"],
        recipient_info["address"],
        str(response["amount"]),
        "cleared",
        entry_id,
    )
    tipper_functions.exec_sql(sql, val)

    if response["status"] == 20:
        subject = "Congrats on receiving your first Nano Tip!"
        message_text = (
            text.WELCOME_TIP
            % (
                response["amount"] / 10 ** 30,
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
            subject = "You just received a new Nano tip!"
            message_text = (
                text.NEW_TIP
                % (
                    response["amount"] / 10 ** 30,
                    recipient_info["address"],
                    receiving_new_balance[0] / 10 ** 30,
                    (
                        receiving_new_balance[1] / 10 ** 30
                        + response["amount"] / 10 ** 30
                    ),
                    response["hash"],
                )
                + text.COMMENT_FOOTER
            )
            send_pm(recipient_info["username"], subject, message_text)
        return response
