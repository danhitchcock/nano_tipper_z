from .sql_scripts import add_subreddit
import click


@click.group()
def cli():
    pass


cli.add_command(add_subreddit)
