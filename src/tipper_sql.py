import time
from datetime import datetime
from shared import PROGRAM_MINIMUM, db, Subreddit, Account

@db.connection_context()
def add_subreddit(
    subreddit,
    reply_to_comments=True,
    footer="",
    status="friendly",
    minimum=PROGRAM_MINIMUM,
):
    sub = Subreddit(
        subreddit=subreddit,
        reply_to_comments=reply_to_comments,
        footer=footer,
        status=status,
        minimum=PROGRAM_MINIMUM
    )
    sub.save(force_insert=True)

@db.connection_context()
def modify_subreddit(subreddit, status):
    Subreddit.update(status=status).where(Subredit.subreddit == subreddit).execute()

@db.connection_context()
def rm_subreddit(subreddit):
    Subreddit.delete().where(Subreddit.subreddit == subreddit).execute()

@db.connection_context()
def backup_keys():
    accounts = Account.select(Account.username, Account.address, Account.private_key)
    with open("../backup", "w") as f:
        for acct in accounts:
            f.write(acct.username + "," + acct.address + "," + acct.private_key + "\n")

@db.connection_context()
def backup_accounts():
    accounts = Account.select()
    with open("../backup_accounts", "w") as f:
        for acct in accounts:
            # TODO - backup other fields
            f.write(acct.username + "," + acct.address + "," + acct.private_key + "\n")

@db.connection_context()
def subreddits():
    results = Subreddit.select()
    for result in results:
        print(f"Subreddit: {result.subreddit}, status: {result.status}")
