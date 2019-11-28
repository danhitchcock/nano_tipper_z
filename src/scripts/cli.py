from .sql_scripts import add_subreddit, list_subreddits
import click


@click.group()
def cli():
    pass


cli.add_command(add_subreddit)
cli.add_command(list_subreddits)
