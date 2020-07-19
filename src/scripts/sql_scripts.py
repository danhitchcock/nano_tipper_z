import click
import tipper_sql
from tipper_sql import MYCURSOR, MYDB
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


@click.command()
def migrate_subreddit_status():
    sql = 'UPDATE subreddits SET status="silent" WHERE status="hostile"'
    MYCURSOR.execute(sql)
    MYDB.commit()

    sql = 'UPDATE subreddits SET status="full" WHERE status="friendly"'
    MYCURSOR.execute(sql)
    MYDB.commit()


@click.command()
@click.option("-u", default=None)
@click.option("-n", default=10)
def pull_history(u, n):
    """
    Pulls n number of records for username u
    :param u:
    :param n:
    :return:
    """
    sql = "SELECT id, username, sql_time, action, amount, comment_id, notes, recipient_username, recipient_address, return_status, comment_text FROM history WHERE username=%s ORDER BY id DESC limit %s"
    val = (u, n)
    if u is None:
        sql = "SELECT id, username, sql_time, action, amount, comment_id, notes, recipient_username, recipient_address, return_status, comment_text FROM history ORDER BY id DESC limit %s"
        val = (n,)
    MYCURSOR.execute(sql, val)
    results = MYCURSOR.fetchall()
    if len(results) == 0:
        LOGGER.info("Username %s not found." % u)
    MYDB.commit()
    LOGGER.info(
        "Printing results: Username, Datetime, action, amount, comment_id, notes_recipient_username, recipient_address"
    )
    for result in results:
        LOGGER.info(result)


@click.command()
@click.argument("u")
def delete_user(u):
    sql = "DELETE FROM accounts WHERE username = %s"
    val = (u,)
    MYCURSOR.execute(sql, val)
    MYDB.commit()


@click.command()
@click.option("-u", default=None)
def list_users(u):
    sql = "SELECT username FROM accounts"
    MYCURSOR.execute(sql)
    results = MYCURSOR.fetchall()
    for result in results:
        LOGGER.info(result)


@click.command()
@click.option("--id", default=None)
def modify_history(id):

    sql = "UPDATE history SET sql_time='2020-06-10 09:21:28' WHERE id=%s"
    MYCURSOR.execute(sql, (id,))
    MYDB.commit()
