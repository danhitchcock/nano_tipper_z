import os
import click

# change the working directory to two levels up
dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(os.path.join(dir_path, "../.."))

from .sql_scripts import (
    subreddit,
    list_subreddits,
    migrate_subreddit_status,
    pull_history,
    delete_user,
    list_users,
    modify_history,
    list_returns,
)
from .rpc_scripts import block_count, address_pendings, all_pendings


@click.group()
def cli():
    pass


cli.add_command(subreddit)
cli.add_command(list_subreddits)
cli.add_command(migrate_subreddit_status)
cli.add_command(block_count)
cli.add_command(pull_history)
cli.add_command(delete_user)
cli.add_command(list_users)
cli.add_command(modify_history)
cli.add_command(address_pendings)
cli.add_command(all_pendings)
cli.add_command(list_returns)
