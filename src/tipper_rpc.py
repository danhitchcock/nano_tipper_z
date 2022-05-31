import json
import qrcode
import requests
from shared import (
    DPOW_TOKEN,
    DEFAULT_URL,
    LOGGER,
    DPOW_USERNAME,
    REP,
    DPOW_ENDPOINT,
    USE_DPOW,
)


def perform_curl(data=None, URL=None, timeout=30):
    if URL is None:
        URL = DEFAULT_URL
    r = requests.post(
        URL, headers={"Content-Type": "application/json"}, data=json.dumps(data)
    )
    return json.loads(r.text)


def send(origin, key, amount, destination, rep=None, work=None):
    """
    Highest level send command. Takes care of everything.
    :param origin:
    :param key:
    :param amount:
    :param destination:
    :param rep:
    :param work:
    :return:
    """
    hash = account_info(origin)["frontier"]
    work = work_generate(hash, True)["work"]
    generated_send_block = send_block(origin, key, amount, destination, work=work)
    results = process_block(generated_send_block)
    return results


def work_generate(hash, dpow=False):
    """
    Generates PoW for a hash. If dpow is set to false, does it on the local node.
    If dpow is set to true, will attempt to use remote dpow server. If there is no response in one second,
    the function will recursively call itself with dpow=false and do it locally.
    :param hash:
    :param dpow:
    :return: dict with 'work' as a key
    """
    # if dpow is globaly disable, disable here
    dpow=False

    if dpow:
        # API call
        try:
            # api token will be in a separate text file
            data = {"api_key": DPOW_TOKEN, "user": DPOW_USERNAME, "hash": hash}
            results = requests.post(DPOW_ENDPOINT, json.dumps(data), timeout=10)
            results = json.loads(results.text)
        except requests.exceptions.Timeout:
            LOGGER.info("Falling back to local POW...")
            return work_generate(hash)
        return results
    else:
        data = {"action": "work_generate", "hash": hash}
    results = perform_curl(data)
    return results


def account_info(account):
    data = {"action": "account_info", "account": account}
    results = perform_curl(data)

    return results


def send_block(origin, key, amount, destination, rep=None, work=None):

    info = account_info(origin)
    balance = int(info["balance"])
    balance = balance - amount
    previous = info["frontier"]
    if rep is None:
        rep = REP
    data = {
        "action": "block_create",
        "type": "state",
        "previous": previous,
        "account": origin,
        "balance": balance,
        "link": destination,
        "representative": rep,
        "key": key,
    }
    if work:
        data["work"] = work

    results = perform_curl(data)
    return results


def send_all(origin, key, destination):
    amount = check_balance(origin)[0]
    if amount != 0:
        return send(origin, key, amount, destination)
    return None


def open_block(account, key, rep=None, work=None):
    """
    :param account: str account to open
    :param key: str account private key
    :param rep: str representative
    :return: str block-string for json
    """
    if rep is None:
        rep = REP
    try:
        account_info(account)["frontier"]
        return "Previous block exists. Use receive."
    except:
        pass
    sent_hash = get_pending(account, -1)["blocks"][0]

    sent_block = get_block_by_hash(sent_hash)
    sent_previous_hash = sent_block["previous"]
    sent_previous_block = get_block_by_hash(sent_previous_hash)
    amount = int(sent_previous_block["balance"]) - int(sent_block["balance"])
    data = {
        "action": "block_create",
        "type": "state",
        "previous": "0",
        "account": account,
        "representative": rep,
        "balance": amount,
        "link": sent_hash,
        "key": key,
    }
    if work:
        data["work"] = work
    results = perform_curl(data)
    return results


def receive_block(account, key, sent_hash, rep=None):
    """
    :param account: str account to open
    :param key: str account private key
    :param rep: str representative
    :return: str block-string for json
    """
    if rep is None:
        rep = REP
    previous = account_info(account)["frontier"]
    sent_block = get_block_by_hash(sent_hash)
    sent_previous_hash = sent_block["previous"]
    sent_previous_block = get_block_by_hash(sent_previous_hash)
    amount = int(sent_previous_block["balance"]) - int(sent_block["balance"])
    amount = check_balance(account)[0] + amount
    data = {
        "action": "block_create",
        "type": "state",
        "previous": previous,
        "account": account,
        "representative": rep,
        "balance": amount,
        "link": sent_hash,
        "key": key,
    }
    results = perform_curl(data)
    return results


def open_account(*argv):
    """
    account, key, rep=None
    """
    results = process_block(open_block(*argv))
    return results


def receive_all(account, key, rep=None):
    hashes = []
    sent_hashes = get_pending(account)["blocks"]
    # print("these are sent hashes. ", sent_hashes)
    if len(sent_hashes) < 1:
        return "No Pending Transactions."
    else:
        for sent_hash in sent_hashes:
            results = process_block(receive_block(account, key, sent_hash, rep))
            hashes.append(results)
    return hashes


def check_balance(account, amount=None, URL=None):
    data = {"action": "account_balance", "account": account}
    results = perform_curl(data, URL)
    if amount is None:
        # print(results)
        return [int(results["balance"]), int(results["pending"])]
    else:
        return int(results["pending"]) == amount


def generate_account():
    data = {"action": "key_create"}
    return perform_curl(data)


def get_previous_hash(account):
    data = {"action": "account_info", "account": account}
    results = perform_curl(data)
    return results["frontier"]


def get_block_by_hash(hash):
    data = {"action": "block", "hash": hash}
    results = perform_curl(data)
    return json.loads(results["contents"])


def get_pending(account, count=-1):
    data = {"action": "pending", "account": account, "count": str(count)}
    results = perform_curl(data)
    # print(results)
    return results


def account_key(account):
    data = {"action": "account_key", "account": account}
    results = perform_curl(data)
    return results


def get_pendings(accounts, count=-1, threshold=None):
    data = {"action": "accounts_pending", "accounts": accounts, "count": str(count)}
    if threshold:
        data["threshold"] = "%s" % (threshold)
    results = perform_curl(data)
    return results


def validate_address(address):
    data = {"action": "validate_account_number", "account": address}
    return perform_curl(data)


def generate_qr(account, amount=0, fill_color="black", back_color="white"):
    account_amount = "xrb:%s?amount=%s" % (account, amount)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(account_amount)
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    return img


def process_block(block):
    data = {"action": "process"}
    data["block"] = block["block"]
    return perform_curl(data)


def open_or_receive(account, key):
    pass
    # print(account, key)
    # print('attempting to receive')
    try:
        hash = open_account(account, key)
    except:
        pass
    try:
        received = receive_all(account, key)
    except:
        pass


def open_or_receive_blocks(account, key, blocks, rep=None):

    work = None
    if rep is None:
        rep = REP

    # if there is a previous block, receive the blocks
    try:
        previous = account_info(account)["frontier"]
    except Exception as e:
        # otherwise, this is an open block.
        previous = 0

    for sent_hash in blocks:
        sent_block = get_block_by_hash(sent_hash)
        sent_previous_hash = sent_block["previous"]
        sent_previous_block = get_block_by_hash(sent_previous_hash)
        # if it's an open block, get work from the dpow server
        if previous == 0:
            account_public_key = account_key(account)["key"]
            work = work_generate(account_public_key, True)["work"]
            # print(account, account_public_key, work)

        amount = int(sent_previous_block["balance"]) - int(sent_block["balance"])
        amount = check_balance(account)[0] + amount
        data = {
            "action": "block_create",
            "type": "state",
            "previous": previous,
            "account": account,
            "representative": rep,
            "balance": amount,
            "link": sent_hash,
            "key": key,
        }
        # if it's an open block, add in our 'open' work
        if work:
            data["work"] = work
        previous = process_block(perform_curl(data))["hash"]
        work = None


def open_or_receive_block(account, key, sent_hash, rep=None):
    work = None
    if rep is None:
        rep = REP

    # if there is a previous block, receive the blocks
    try:
        previous = account_info(account)["frontier"]
    except Exception as e:
        # print("It's an open block. ", e)
        # otherwise, this is an open block.
        previous = 0

    sent_block = get_block_by_hash(sent_hash)
    sent_previous_hash = sent_block["previous"]
    sent_previous_block = get_block_by_hash(sent_previous_hash)
    # if it's an open block, get work from the dpow server
    if previous == 0:
        account_public_key = account_key(account)["key"]
        # print("Opening.")
        work = work_generate(account_public_key, True)["work"]
        # print(account, account_public_key, work)
    else:
        work = work_generate(previous, True)["work"]

    amount = int(sent_previous_block["balance"]) - int(sent_block["balance"])
    amount = check_balance(account)[0] + amount
    data = {
        "action": "block_create",
        "type": "state",
        "previous": previous,
        "account": account,
        "representative": rep,
        "balance": amount,
        "link": sent_hash,
        "key": key,
    }
    # if it's an open block, add in our 'open' work
    if work:
        data["work"] = work
    previous = process_block(perform_curl(data))["hash"]
    work = None
