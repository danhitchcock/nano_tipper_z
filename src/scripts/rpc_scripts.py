import click
import tipper_rpc
from shared import MYCURSOR, MYDB, to_raw


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
    pendings = tipper_rpc.get_pendings(addresses, threshold=to_raw(threshold))
    for username, address in zip(usernames, addresses):
        if pendings["blocks"][address]:
            print(username, address, pendings["blocks"][address])

@click.command()
def total_funds():
    MYCURSOR.execute("SELECT username, address FROM accounts")
    myresult = MYCURSOR.fetchall()
    usernames = [str(result[0]) for result in myresult]
    addresses = [str(result[1]) for result in myresult]
    MYDB.commit()
    balance = 0
    num_over_10 = 0
    num_over_1 = 0
    num_over_p5 = 0
    num_zero = 0
    for username, address in zip(usernames, addresses):
        new_balance = tipper_rpc.check_balance(address)
        user_balance =new_balance[0] / 10**30 + new_balance[1] / 10**30
        balance += user_balance
        if user_balance >=10:
            num_over_10 +=1
            num_over_1+=1
            num_over_p5+=1
        elif user_balance >=1:
            num_over_1+=1
            num_over_p5+=1
        elif user_balance >=.5:
            num_over_p5+=1
        if user_balance <=.0000001:
            num_zero+=1

    print("Total Nano: ", balance)
    print("Total Over 10: ", num_over_10)
    print("Total Over 1: ", num_over_1)
    print("Total Over 0.5: ", num_over_p5)
    print("Total 0: ", num_zero)

