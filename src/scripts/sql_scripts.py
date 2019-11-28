import click
import tipper_sql


@click.command()
@click.argument("--subreddit")
@click.option("--status", default="friendly")
def add_subreddit(subreddit, status):
    tipper_sql.add_subreddit(subreddit, True, "", status)


@click.command()
def list_subreddits():
    print("Listing")
    tipper_sql.subreddits()
