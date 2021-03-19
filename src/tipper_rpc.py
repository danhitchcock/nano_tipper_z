import json
import uuid
import qrcode
import requests
import nanopy
from shared import (
    DEFAULT_URL,
    CURRENCY,
    WALLET_ID,
    RandomUtil,
    Validators
)

if CURRENCY == "Banano":
    nanopy.account_prefix = 'ban_'
    nanopy.standard_exponent = 29
else:
    nanopy.account_prefix = 'nano_'

def perform_curl(data=None, URL=None, timeout=30):
    if URL is None:
        URL = DEFAULT_URL
    r = requests.post(
        URL, headers={"Content-Type": "application/json"}, data=json.dumps(data)
    )
    return json.loads(r.text)


def send(origin, amount, destination):
    """
    Highest level send command. Takes care of everything.
    :param origin:
    :param amount:
    :param destination:
    :return:
    """
    uid = uuid.uuid4().hex
    req = {
        "action":"send",
        "id": uid,
        "wallet": WALLET_ID,
        "source": origin,
        "destination": destination,
        "amount": amount
    }
    return perform_curl(req)

def check_balance(account, amount=None, URL=None):
    data = {"action": "account_balance", "account": account}
    results = perform_curl(data, URL)
    if amount is None:
        # print(results)
        return int(results["balance"]) + int(results["pending"])
    else:
        return int(results["pending"]) == amount

def generate_account():
    pk = RandomUtil.generate_seed()
    data = {"action": "wallet_add", "wallet": WALLET_ID, "key": pk}
    res = perform_curl(data)
    if "account" in res:
        return res["account"], pk
    return None, pk

def get_pending(account, count=-1):
    data = {"action": "pending", "account": account, "count": str(count)}
    results = perform_curl(data)
    # print(results)
    return results

def validate_address(address):
    return Validators.is_valid_address(address)

def generate_qr(account, amount=0, fill_color="black", back_color="white"):
    if CURRENCY == "Nano":
        account_amount = "xrb:%s?amount=%s" % (account, amount)
    else:
        account_amount = "ban:%s?amount=%s" % (account, amount)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(account_amount)
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    return img