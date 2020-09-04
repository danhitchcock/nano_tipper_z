import click
import tipper_rpc
from shared import MYCURSOR, MYDB
from tipper_functions import nano_to_raw

@click.command()
def block_count():
    data = {"action": "block_count"}
    print(tipper_rpc.perform_curl(data))


@click.command()
@click.argument("account")
def address_pendings(account):
    print(tipper_rpc.get_pending(account))


@click.command()
@click.argument("threshold")
def all_pendings(threshold):
    threshold = float(threshold)
    MYCURSOR.execute("SELECT username, address FROM accounts")
    myresult = MYCURSOR.fetchall()
    usernames = [str(result[0]) for result in myresult]
    addresses = [str(result[1]) for result in myresult]

    MYDB.commit()
    pendings = tipper_rpc.get_pendings(addresses, threshold=nano_to_raw(threshold))
    for username, address in zip(usernames, addresses):
        if pendings['blocks'][address]:
            print(username, address, int(pendings['blocks'][address])/10**30)

