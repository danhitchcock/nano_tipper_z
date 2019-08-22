import json
import qrcode
import requests
import configparser

# access the sql library
config = configparser.ConfigParser()
config.read('./tipper.ini')
print(config.sections())
dpow_token = config['NODE']['dpow_token']
default_url = config['NODE']['default_url']

def perform_curl(data=None, URL=None, timeout=30):
    if URL is None:
        URL = default_url
    r = requests.post(URL, headers={"Content-Type": "application/json"}, data=json.dumps(data))
    return json.loads(r.text)


def send_w(origin, key, amount, destination, rep=None, work=None):
    hash = account_info(origin)['frontier']
    work = work_generate(hash, True)['work']
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
    if dpow:
        # API call
        try:
            # api token will be in a separate text file
            data = {
                "api_key": dpow_token,
                "user": 'zily_reddit',
                "hash": hash
            }
            results = requests.post('https://dpow.nanocenter.org/service/', json.dumps(data), timeout=10)
            results = json.loads(results.text)
        except requests.exceptions.Timeout:
            return work_generate(hash)
        return results
    else:
        data = {
            "action": "work_generate",
            "hash": hash
        }
    results = perform_curl(data)
    return results


def account_info(account):
    data = {
        'action': 'account_info',
        'account': account
    }
    results = perform_curl(data)

    return results


def send_block(origin, key, amount, destination, rep=None, work=None):

    info = account_info(origin)
    balance = int(info['balance'])
    balance = balance - amount
    previous = info['frontier']
    if rep is None:
        rep = "xrb_1thingspmippfngcrtk1ofd3uwftffnu4qu9xkauo9zkiuep6iknzci3jxa6"
    data = {
        "action": "block_create",
        "type": "state",
        "previous": previous,
        "account": origin,
        "balance": balance,
        "link": destination,
        "representative": rep,
        "key": key
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
        rep = "xrb_1thingspmippfngcrtk1ofd3uwftffnu4qu9xkauo9zkiuep6iknzci3jxa6"
    try:
        get_previous_hash(account)
        return "Previous block exists. Use receive."
    except:
        pass
    sent_hash = get_pending(account, -1)["blocks"][0]

    sent_block = get_block_by_hash(sent_hash)
    sent_previous_hash = sent_block['previous']
    sent_previous_block = get_block_by_hash(sent_previous_hash)
    amount = (int(sent_previous_block['balance']) - int(sent_block['balance']))
    data = {
        'action': 'block_create',
        'type': 'state',
        'previous': '0',
        'account': account,
        'representative': rep,
        'balance': amount,
        'link': sent_hash,
        'key': key,
    }
    if work:
        data['work'] = work
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
        rep = "xrb_1thingspmippfngcrtk1ofd3uwftffnu4qu9xkauo9zkiuep6iknzci3jxa6"
    previous = get_previous_hash(account)
    sent_block = get_block_by_hash(sent_hash)
    sent_previous_hash = sent_block['previous']
    sent_previous_block = get_block_by_hash(sent_previous_hash)
    amount = (int(sent_previous_block['balance']) - int(sent_block['balance']))
    amount = check_balance(account)[0] + amount
    data = {
        'action': 'block_create',
        'type': 'state',
        'previous': previous,
        'account': account,
        'representative': rep,
        'balance': amount,
        'link': sent_hash,
        'key': key,
    }
    results = perform_curl(data)
    return results


def send(*argv):
    """
    origin, key, amount, destination, rep=None
    """
    results = process_block(send_block(*argv))
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
    #print("these are sent hashes. ", sent_hashes)
    if len(sent_hashes) < 1:
        return "No Pending Transactions."
    else:
        for sent_hash in sent_hashes:
            results = process_block(receive_block(account, key, sent_hash, rep))
            hashes.append(results)
    return hashes


def check_balance(account, amount=None, URL=None):
    data = {
        "action": "account_balance",
        "account": account
    }
    results = perform_curl(data, URL)
    if amount is None:
        #print(results)
        return [int(results['balance']), int(results['pending'])]
    else:
        return int(results['pending']) == amount


def generate_account():
    data = {"action": "key_create"}
    return (perform_curl(data))


def get_previous_hash(account):
    data = {
        "action": "account_history",
        "account": account,
        "count": "1"
    }
    results = perform_curl(data)
    return results['history'][0]['hash']


def get_block_by_hash(hash):
    data = {
        "action": "block",
        "hash": hash
    }
    results = perform_curl(data)
    return json.loads(results['contents'])


def get_pending(account, count=-1):
    data = {
        "action": "pending",
        "account": account,
        "count": str(count)
    }
    results = perform_curl(data)
    #print(results)
    return results


def account_key(account):
    data = {
        "action": "account_key",
        "account": account,
    }
    results = perform_curl(data)
    return results


def get_pendings(accounts, count=-1, threshold=None):
    data = {
        "action": "accounts_pending",
        "accounts": accounts,
        "count": str(count)
    }
    if threshold:
        data['threshold'] = "%s" % (threshold)
    results = perform_curl(data)
    return results


def validate_address(address):
    data = {
      "action": "validate_account_number",
      "account": address
    }
    return perform_curl(data)


def generate_qr(account, amount=0, fill_color="black", back_color="white"):
    account_amount = 'xrb:%s?amount=%s' % (account, amount)
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
    data["block"] = block['block']
    return perform_curl(data)


def nano_to_raw(amount):
    return round(int(amount*10**30), -20)


def raw_to_nano(amount):
    return amount/10**30


def open_or_receive(account, key):
    pass
    #print(account, key)
    #print('attempting to receive')
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
        rep = "xrb_1thingspmippfngcrtk1ofd3uwftffnu4qu9xkauo9zkiuep6iknzci3jxa6"

    # if there is a previous block, receive the blocks
    try:
        previous = get_previous_hash(account)
    except Exception as e:
        print("It's an open block. ", e)
        # otherwise, this is an open block.
        previous = 0

    for sent_hash in blocks:
        sent_block = get_block_by_hash(sent_hash)
        sent_previous_hash = sent_block['previous']
        sent_previous_block = get_block_by_hash(sent_previous_hash)
        # if it's an open block, get work from the dpow server
        if previous == 0:
            account_public_key = account_key(account)['key']
            print('Opening.')
            work = work_generate(account_public_key, True)['work']
            # print(account, account_public_key, work)

        amount = (int(sent_previous_block['balance']) - int(sent_block['balance']))
        amount = check_balance(account)[0] + amount
        data = {
            'action': 'block_create',
            'type': 'state',
            'previous': previous,
            'account': account,
            'representative': rep,
            'balance': amount,
            'link': sent_hash,
            'key': key
        }
        # if it's an open block, add in our 'open' work
        if work:
            data['work'] = work
        previous = process_block(perform_curl(data))['hash']
        work = None


def open_or_receive_block(account, key, sent_hash, rep=None):
    work = None
    if rep is None:
        rep = "xrb_1thingspmippfngcrtk1ofd3uwftffnu4qu9xkauo9zkiuep6iknzci3jxa6"

    # if there is a previous block, receive the blocks
    try:
        previous = get_previous_hash(account)
    except Exception as e:
        print("It's an open block. ", e)
        # otherwise, this is an open block.
        previous = 0


    sent_block = get_block_by_hash(sent_hash)
    sent_previous_hash = sent_block['previous']
    sent_previous_block = get_block_by_hash(sent_previous_hash)
    # if it's an open block, get work from the dpow server
    if previous == 0:
        account_public_key = account_key(account)['key']
        print('Opening.')
        work = work_generate(account_public_key, True)['work']
        # print(account, account_public_key, work)
    else:
        work = work_generate(previous, True)['work']

    amount = (int(sent_previous_block['balance']) - int(sent_block['balance']))
    amount = check_balance(account)[0] + amount
    data = {
        'action': 'block_create',
        'type': 'state',
        'previous': previous,
        'account': account,
        'representative': rep,
        'balance': amount,
        'link': sent_hash,
        'key': key
    }
    # if it's an open block, add in our 'open' work
    if work:
        data['work'] = work
    previous = process_block(perform_curl(data))['hash']
    work = None

#data = {
#        "action": "account_history",
#        "account": 'xrb_1wnc4mmgizw95up3yshqt7uexmphuz5ezx3o3kb1n1jhh6swbg18o7nrc6zn',
#        "count": "10"
#    }

# f = perform_curl(data)
# for item in f['history']:
#     print(item)
if __name__=="__main__":
    open_account('nano_1z514qfsnb54tqmu5zrdxcprstr1m4b17ornz8r9km3o3zg6k1a3bshzjswd', 'A3333365E5F27CA63F9389565FE26901886D8E4D71C38A2DF0F0C8F962B2AC32')
    # send('nano_37w5ticr1xkbxru31insi7izdbnexs6wsfie6j9oh3ya5ydb43iumukftsfk', 'E937F6D3E8BE8444A302ECCA1A80A0C559E7C60F046203B17472B57A31D4ED05', .1, 'xrb_3h6wcsrwq9yowtkjscyswb3z6cddgfxrmn5prw4qro6fgut8dpip8m6ppagt' )
