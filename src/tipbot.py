import time
import requests
import json
from time import sleep

from tipper_rpc import get_pendings, open_or_receive_block
import shared
from shared import (
    MYCURSOR,
    MYDB,
    REDDIT,
    PROGRAM_MINIMUM,
    to_raw,
)

from message_functions import handle_message

from tipper_functions import (
    parse_action,
    return_transactions,
    return_transactions_new,
    update_status_message,
)
from comment_functions import handle_comment


# how often we poll for new transactions
CYCLE_TIME = 6


def stream_comments_messages():
    """
    # generator to stream comments and messages to the main loop at the bottom, and contains the auto_receive functionality.
    # Maybe this wasn't necessary, but I never get to use generators.
    # To check for new messages and comments, the function scans the subreddits and inbox every 6 seconds and builds a
    # set of current message. I compare the old set with the new set.
    :return:
    """
    previous_time = time.time()
    # previous_comments = {comment for comment in shared.SUBREDDITS.comments()}
    previous_comments = set()
    previous_messages = {message for message in REDDIT.inbox.all(limit=25)}
    previous_all = previous_comments.union(previous_messages)

    while True:
        try:
            sleep(CYCLE_TIME - (time.time() - previous_time))
        except ValueError:
            pass
        previous_time = time.time()

        # check for new comments
        # updated_comments = {comment for comment in shared.SUBREDDITS.comments()}
        updated_comments = set()
        updated_messages = {message for message in REDDIT.inbox.all(limit=25)}
        updated_all = updated_comments.union(updated_messages)
        new = updated_all - previous_all
        previous_all = updated_all

        if len(new) >= 1:
            for item in new:
                yield item
        else:
            yield None


def auto_receive():
    count = 0
    MYCURSOR.execute("SELECT username, address, private_key FROM accounts")
    myresult = MYCURSOR.fetchall()

    addresses = [str(result[1]) for result in myresult]
    private_keys = [str(result[2]) for result in myresult]
    MYDB.commit()
    pendings = get_pendings(addresses, threshold=to_raw(PROGRAM_MINIMUM))
    # get any pending blocks from our address
    for address, private_key in zip(addresses, private_keys):
        # allow 5 transactions to be received per cycle. If the bot gets transaction spammed, at least it won't be
        # locked up receiving.
        if count >= 5:
            break
        try:
            if pendings["blocks"][address]:
                for sent_hash in pendings["blocks"][address]:
                    # address, private_key, dictionary where the blocks are the keys
                    open_or_receive_block(address, private_key, sent_hash)
                    count += 1
                    if count >= 2:
                        break

        except KeyError:
            pass
        except Exception as e:
            print("Autoreceive error: ",pendings, e)


def main_loop():
    # our "subreddits" object, not to be confused with shared.SUBREDDITS
    actions = {
        "message": handle_message,
        "comment": handle_comment,
        "faucet_tip": handle_message,
        "ignore": lambda x: None,
        "replay": lambda x: None,
        None: lambda x: None,
    }
    inactive_timer = time.time()
    inactivate_timer_new = time.time()
    receive_timer = time.time()
    subreddit_timer = time.time()
    usd_timer = time.time()

    update_status_message()
    return_transactions()
    return_transactions_new()
    for action_item in stream_comments_messages():
        action = parse_action(action_item)
        actions[action](action_item)

        # run the inactive script at the end of the loop; every 12 hours
        if time.time() - inactive_timer > 43200:
            inactive_timer = time.time()
            return_transactions()

        # run the inactive script at the end of the loop; every 12 hours
        if time.time() - inactivate_timer_new > 43200:
            inactivate_timer_new = time.time()
            return_transactions_new()

        # run the receive script every 20 seconds
        if time.time() - receive_timer > 20:
            receive_timer = time.time()
            # auto_receive()

        # refresh subreddit status every 5 minutes
        if time.time() - subreddit_timer > 300:
            subreddit_timer = time.time()
            shared.SUBREDDITS = shared.get_subreddits()
            update_status_message()

        # refresh USD amount every 5 minutes
        if time.time() - usd_timer > 300:
            try:
                usd_timer = time.time()
                url = "https://min-api.cryptocompare.com/data/price?fsym={}&tsyms={}".format(
                    "Nano", "USD"
                )
                results = requests.get(url, timeout=1)
                results = json.loads(results.text)
                shared.USD_VALUE = float(results["USD"])
            except requests.exceptions.ReadTimeout:
                pass


if __name__ == "__main__":
    main_loop()
