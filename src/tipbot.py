import time

from time import sleep

import shared
from shared import REDDIT, PROGRAM_MINIMUM, SUBREDDITS, to_raw

from message_functions import handle_message

from tipper_functions import parse_action
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
    previous_comments = {comment for comment in SUBREDDITS.comments()}
    previous_messages = {message for message in REDDIT.inbox.all(limit=25)}
    previous_all = previous_comments.union(previous_messages)

    while True:
        try:
            sleep(CYCLE_TIME - (time.time() - previous_time))
        except ValueError:
            pass
        previous_time = time.time()

        # check for new comments
        updated_comments = {comment for comment in SUBREDDITS.comments()}
        updated_messages = {message for message in REDDIT.inbox.all(limit=25)}
        updated_all = updated_comments.union(updated_messages)
        new = updated_all - previous_all
        previous_all = updated_all

        if len(new) >= 1:
            for item in new:
                yield item
        else:
            yield None

def main_loop():
    global SUBREDDITS
    actions = {
        "message": handle_message,
        "comment": handle_comment,
        "faucet_tip": handle_message,
        "ignore": lambda x: None,
        "replay": lambda x: None,
        None: lambda x: None,
    }
    subreddit_timer = time.time()
    for action_item in stream_comments_messages():
        action = parse_action(action_item)
        actions[action](action_item)

        # refresh subreddit status every 5 minutes
        if time.time() - subreddit_timer > 300:
            subreddit_timer = time.time()
            shared.SUBREDDITS = shared.get_subreddits()
            SUBREDDITS = shared.SUBREDDITS


if __name__ == "__main__":
    main_loop()
