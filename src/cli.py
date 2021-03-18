import os
import click
import tipper_sql
import tipper_rpc
from shared import LOGGER, to_raw

@click.group()
def cli():
    pass

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
def block_count():
    data = {"action": "block_count"}
    print(tipper_rpc.perform_curl(data))


@click.command()
@click.argument("account")
def address_pendings(account):
    print(tipper_rpc.get_pending(account))



cli.add_command(subreddit)
cli.add_command(list_subreddits)
cli.add_command(block_count)
cli.add_command(address_pendings)

if __name__ == '__main__':
    cli()