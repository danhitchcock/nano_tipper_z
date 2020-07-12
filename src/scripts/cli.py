import click
from .sql_scripts import (
    add_subreddit,
    list_subreddits,
    migrate_subreddit_status,
    pull_history,
    delete_user,
    list_users,
)
from .rpc_scripts import block_count


@click.group()
def cli():
    pass


cli.add_command(add_subreddit)
cli.add_command(list_subreddits)
cli.add_command(migrate_subreddit_status)
cli.add_command(block_count)
cli.add_command(pull_history)
cli.add_command(delete_user)
cli.add_command(list_users)
