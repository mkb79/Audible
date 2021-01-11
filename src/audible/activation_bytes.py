import base64
import hashlib
import pathlib
import struct
import urllib.parse
from typing import Optional, TYPE_CHECKING, Union

import httpx

from .exceptions import AuthFlowError

if TYPE_CHECKING:
    import audible


def get_player_id() -> str:
    """Build a software player Id."""
    player_id = base64.encodebytes(hashlib.sha1(b"").digest()).rstrip()
    return player_id.decode("ascii")


def get_player_token(auth: "audible.Authenticator") -> str:
    """Fetches a player token for further authentication.

    Args:    
        auth: The Authenticator.

    Returns:
        The player token.
    """
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

    query = resp.url.query.decode()
    parsed_query = urllib.parse.parse_qs(query)
    player_token = parsed_query.get("playerToken")[0]
    return player_token


def extract_activation_bytes(data: bytes) -> str:
    """Extracts the activation bytes from activation blob.

    Args:    
        data: A activation blob returned by ``fetch_activation`` function
    
    Returns:
        The extracted activation bytes.
    
    Raises:
        ValueError: If `data` is not a valid activation blob.
    """
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


def fetch_activation(player_token: str) -> bytes:
    """Fetches the activation blob with player tokenfrom Audible server.

    Args:    
        player_token: A player token returned by ``get_player_token`` function.
    
    Returns:
        The activation blob.
    """
    url = "https://www.audible.com/license/licenseForCustomerToken"

    # register params
    rparams = {"customer_token": player_token}

    # deregister params
    dparams = {"customer_token": player_token, "action": "de-register"}

    headers = {"User-Agent": "Audible Download Manager"}
    with httpx.Client(headers=headers) as session:
        session.get(url, params=dparams)
        try:
            resp = session.get(url, params=rparams)
            return resp.content
        finally:
            session.get(url, params=dparams)


def fetch_activation_sign_auth(auth: "audible.Authenticator") -> bytes:
    """Fetches the activation blob with sign authentication from Audible server.

    Args:    
        auth: A ``Authenticator`` instance with valid `'adp_token`` and 
            ``device_private_cert``.
    
    Returns:
        The activation blob.
    """
    assert "signing" in auth.available_auth_modes

    url = "https://www.audible.com/license/token"
    params = {
        "player_manuf": "Audible,iPhone",
        "action": "register",
        "player_model": "iPhone"
    }
    with httpx.Client(auth=auth) as client:    
        resp = client.get(url, params=params)
        return resp.content


def get_activation_bytes(auth: "audible.Authenticator",
                         filename: Optional[Union[str, pathlib.Path]] = None,
                         extract: bool = True) -> Union[str, bytes]:
    """Fetches the activation blob from Audible and extracts the bytes.

    Args:    
        auth: The Authenticator.
        filename: The filename to save the activation blob (Default: None).
        extract: If True, returns the extracted activation bytes otherwise
            the whole activation blob (Default: True).
    
    Returns:
        The activation bytes or activation blob.
    """
    auth_modes = auth.available_auth_modes
    if "signing" in auth_modes:
        activation = fetch_activation_sign_auth(auth)
    elif "cookies" in auth_modes:
        player_token = get_player_token(auth)
        activation = fetch_activation(player_token)
    else:
        raise AuthFlowError("No valid auth mode to fetch activation bytes.")

    pathlib.Path(filename).write_bytes(activation) if filename else ""
    if extract:
        activation = extract_activation_bytes(activation)

    return activation
