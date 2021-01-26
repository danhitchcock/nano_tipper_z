import os
import click

# change the working directory to two levels up
dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(os.path.join(dir_path, "../.."))

from .sql_scripts import (
    subreddit,
    list_subreddits
)
from .rpc_scripts import block_count, address_pendings

@click.group()
def cli():
    pass


cli.add_command(subreddit)
cli.add_command(list_subreddits)
cli.add_command(block_count)
cli.add_command(address_pendings)