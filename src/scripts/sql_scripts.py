import click
import tipper_sql
from tipper_sql import mycursor, mydb


@click.command()
@click.argument("subreddit")
@click.option("--status", default="full")
def add_subreddit(subreddit, status):
    if status not in ["full", "minimal", "silent"]:
        raise ValueError(f"'{status}' is not an acceptable subreddit status.")
    try:
        tipper_sql.add_subreddit(subreddit, True, "", status)
    except:
        tipper_sql.modify_subreddit(subreddit, status)


@click.command()
def list_subreddits():
    tipper_sql.subreddits()


@click.command()
def migrate_subreddit_status():
    sql = 'UPDATE subreddits SET status="silent" WHERE status="hostile"'
    mycursor.execute(sql)
    mydb.commit()

    sql = 'UPDATE subreddits SET status="full" WHERE status="friendly"'
    mycursor.execute(sql)
    mydb.commit()
