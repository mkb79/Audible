import base64
import hashlib
import pathlib
import struct
from urllib.parse import parse_qs

import httpx


def get_player_id():
    player_id = base64.encodebytes(hashlib.sha1(b"").digest()).rstrip()
    return player_id.decode("ascii")


def get_player_token(auth) -> str:
    params = {
        "ipRedirectOverride": True,
        "playerType": "software",
        "bp_ua": "y",
        "playerModel": "Desktop",
        "playerId": get_player_id(),
        "playerManufacturer": "Audible",
        "serial": ""
    }

    url = f"https://www.audible.{auth.locale.domain}/player-auth-token"
    with httpx.Client(cookies=auth.website_cookies) as session:
        resp = session.get(url, params=params)

    query = resp.url.query
    parsed_query = parse_qs(query)
    player_token = parsed_query.get("playerToken")[0]
    return player_token


def extract_activation_bytes(data):
    if (b"BAD_LOGIN" in data or b"Whoops" in data) or \
            b"group_id" not in data:
        print(data)
        print("\nActivation failed! ;(")
        raise ValueError("data wrong")

    # https://github.com/kennedn/kindlepass/blob/master/kindlepass/kindlepass.py

    # Audible returns activation that contains metadata, extracting 0x238 bytes
    # from the end discards this metadata.
    data = data[-0x238:]

    # Strips newline characters from activation body
    fmt = "70s1x" * 8
    data = b''.join(struct.unpack(fmt, data))

    return "{:x}".format(*struct.unpack("<I", data[:4]))


def fetch_activation(player_token):
    url = "https://www.audible.com/license/licenseForCustomerToken"

    # register params
    rparams = {"customer_token": player_token}

    # deregister params
    dparams = {
        "customer_token": player_token,
        "action": "de-register"
    }

    headers = {"User-Agent": "Audible Download Manager"}
    with httpx.Client(headers=headers) as session:
        session.get(url, params=dparams)
        try:
            resp = session.get(url, params=rparams)
            return resp.content
        finally:
            session.get(url, params=dparams)


def get_activation_bytes(auth: , filename=None, extract=True):
    """Get Activation bytes from Audible
    
    :param auth: the Authenticator
    :type auth: audible.Authenticator
    :param filename: [Optional] filename to save the activation blob
    :type filename: string, pathlib.Path
    :param extract: [Optional] if True, returns the extracted activation
                    bytes otherwise the whole activation blob
    :type extract: bool
    """
    player_token = get_player_token(auth)
    activation = fetch_activation(player_token)
    pathlib.Path(filename).write_bytes(activation) if filename else ""

    if extract:
        activation = extract_activation_bytes(activation)

    return activation_bytes
