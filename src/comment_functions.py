import datetime
from shared import (
    MYDB,
    MYCURSOR,
    COMMENT_FOOTER,
    DONATE_COMMANDS,
    TIP_COMMANDS,
    PROGRAM_MINIMUM,
    WELCOME_TIP,
    NEW_TIP,
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

    sql = "SELECT status FROM subreddits WHERE subreddit=%s"
    val = (str(message.subreddit).lower(),)
    MYCURSOR.execute(sql, val)
    results = MYCURSOR.fetchall()

    if len(results) == 0:
        subreddit_status = "silent"
    else:
        subreddit_status = results[0][0]

    # if it is a top level reply and the subreddit is friendly
    if (str(message.parent_id)[:3] == "t3_") and (
        subreddit_status in ["friendly", "full"]
    ):
        message.reply(response + COMMENT_FOOTER)
    # otherwise, if the subreddit is friendly (and reply is not top level) or subreddit is minimal
    elif subreddit_status in ["friendly", "minimal", "full"]:
        message.reply(response + COMMENT_FOOTER)
    elif subreddit_status in ["hostile", "silent"]:
        # it's a hostile place, no posts allowed. Will need to PM users
        message_recipient = str(message.author)
        subject = "Your Nano Tip Status"
        message_text = response + COMMENT_FOOTER
        sql = "INSERT INTO messages (username, subject, message) VALUES (%s, %s, %s)"
        val = (message_recipient, subject, message_text)
        MYCURSOR.execute(sql, val)
        MYDB.commit()
    elif subreddit_status == "custom":
        # not sure what to do with this yet.
        pass


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

    new_account = False
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
        response["amount"] = parse_raw_amount(parsed_text)
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

    # check if amount is above subreddit minimum. Don't worry about repsonse yet
    response["subreddit"] = str(message.subreddit).lower()
    sql = "SELECT status FROM subreddits WHERE subreddit=%s"
    val = (response["subreddit"],)
    results = tipper_functions.query_sql(sql, val)
    if len(results) == 0:
        response["subreddit_minimum"] = 1
    elif results[0][0] in ["friendly", "minimal", "silent"]:
        response["subreddit_minimum"] = 0
    else:
        response["subreddit_minimum"] = 1

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
        parent_author = str(message.parent.author)
        recipient_info = tipper_functions.account_info(parent_author)
        if not recipient_info:
            response["status"] = 20
            recipient_info = tipper_functions.add_new_account(parent_author)
            new_account = True

    elif parsed_text[0] in DONATE_COMMANDS:
        results = tipper_functions.query_sql(
            "FROM projects SELECT address WHERE project = %s", (parsed_text[2],)
        )
        if len(results) <= 0:
            return "No Nanocenter project named %s was found." % parsed_text[2]
        recipient_info = {
            "username": parsed_text[2],
            "address": results[0][0],
            "minimum": -1,
        }
        response["status"] = 40
    else:
        return "Something strange happened."

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
    print(recipient_info)
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
        return (
            "Donated ```%.4g Nano``` to Nanocenter Project %s -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)"
            % (response["amount"] / 10 ** 30, recipient_info["username"], sent)
        )

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

    if new_account:
        subject = "Congrats on receiving your first Nano Tip!"
        message_text = (
            WELCOME_TIP
            % (
                response["amount"] / 10 ** 30,
                recipient_info["address"],
                recipient_info["address"],
            )
            + COMMENT_FOOTER
        )
        send_pm(recipient_info["username"], subject, message_text)
        response["status"] = 20
        return response
        return (
            "Creating a new account for /u/%s and "
            "sending ```%.4g Nano```. [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)"
            % (recipient_info["username"], response["amount"] / 10 ** 30, sent)
        )
    else:

        if not recipient_info["silence"]:
            receiving_new_balance = check_balance(recipient_info["address"])
            subject = "You just received a new Nano tip!"
            message_text = (
                NEW_TIP
                % (
                    response["amount"] / 10 ** 30,
                    recipient_info["address"],
                    receiving_new_balance[0] / 10 ** 30,
                    (
                        receiving_new_balance[1] / 10 ** 30
                        + response["amount"] / 10 ** 30
                    ),
                    sent["hash"],
                )
                + COMMENT_FOOTER
            )
            send_pm(recipient_info["username"], subject, message_text)
        response["status"] = 10
        return response

        return (
            "Sent ```%.4g Nano``` to /u/%s -- [Transaction on Nano Crawler](https://nanocrawler.cc/explorer/block/%s)"
            % (response["amount"] / 10 ** 30, recipient_info["username"], sent)
        )
