import click
from .sql_scripts import add_subreddit, list_subreddits, migrate_subreddit_status
from .rpc_scripts import block_count


@click.group()
def cli():
    pass


cli.add_command(add_subreddit)
cli.add_command(list_subreddits)
cli.add_command(migrate_subreddit_status)
cli.add_command(block_count)
