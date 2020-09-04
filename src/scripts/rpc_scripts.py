import click
import tipper_rpc


@click.command()
def block_count():
    data = {"action": "block_count"}
    print(tipper_rpc.perform_curl(data))


@click.command()
@click.argument("account")
def address_pendings(account):
    print(tipper_rpc.get_pending(account))
