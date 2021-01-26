import click
import tipper_sql
from shared import LOGGER

@click.command()
@click.argument("subreddit")
@click.option("--status", default="full")
@click.option("--delete", "-d", is_flag=True)
def subreddit(subreddit, status, delete):
    if delete:
        print("deleting")
        tipper_sql.rm_subreddit(subreddit)

    else:
        if status not in ["full", "minimal", "silent"]:
            raise ValueError(f"'{status}' is not an acceptable subreddit status.")
        try:
            tipper_sql.add_subreddit(subreddit, True, "", status)
        except:
            tipper_sql.modify_subreddit(subreddit, status)


@click.command()
def list_subreddits():
    tipper_sql.subreddits()
