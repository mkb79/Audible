import base64
import binascii
import json
import math
import struct
from datetime import datetime
from typing import List, Tuple, Union

# constants used for encrypt/decrypt metadata
CONSTANTS = [1888420705, 2576816180, 2347232058, 874813317]


def raw_xxtea(v: List, n: int, k: Union[List, Tuple]) -> int:
    assert isinstance(v, list)
    assert isinstance(k, (list, tuple))
    assert isinstance(n, int)

    def mx():
        return ((z >> 5) ^ (y << 2)) + ((y >> 3) ^ (z << 4)) ^ (sum_ ^ y) + (
                    k[(p & 3) ^ e] ^ z)

    def u32(x):
        return x % 2 ** 32

    y = v[0]
    sum_ = 0
    delta = 2654435769
    if n > 1:  # Encoding
        z = v[n - 1]
        q = int(6 + (52 / n // 1))
        while q > 0:
            q -= 1
            sum_ = u32(sum_ + delta)
            e = u32(sum_ >> 2) & 3
            p = 0
            while p < n - 1:
                y = v[p + 1]
                z = v[p] = u32(v[p] + mx())
                p += 1
            y = v[0]
            z = v[n - 1] = u32(v[n - 1] + mx())
        return 0

    if n < -1:  # Decoding
        n = -n
        q = int(6 + (52 / n // 1))
        sum_ = u32(q * delta)
        while sum_ != 0:
            e = u32(sum_ >> 2) & 3
            p = n - 1
            while p > 0:
                z = v[p - 1]
                y = v[p] = u32(v[p] - mx())
                p -= 1
            z = v[n - 1]
            y = v[0] = u32(v[0] - mx())
            sum_ = u32(sum_ - delta)
        return 0
    return 1


def _bytes_to_longs(data: Union[str, bytes]) -> List[int]:
    data_bytes = data.encode() if isinstance(data, str) else data

    return [int.from_bytes(data_bytes[i:i + 4], "little")
            for i in range(0, len(data_bytes), 4)]


def _longs_to_bytes(data: List[int]) -> bytes:
    return b"".join([i.to_bytes(4, 'little') for i in data])


def _generate_hex_checksum(data: str) -> str:
    checksum = binascii.crc32(data.encode()) % 2 ** 32
    return format(checksum, "X")


class XXTEAException(Exception):
    pass


class XXTEA:
    """XXTEA wrapper class.
    
    Easy to use and compatible (by duck typing) with the Blowfish class.

    Note:    
        Partial copied from https://github.com/andersekbom/prycut and ported 
        from PY2 to PY3
    """

    def __init__(self, key: Union[str, bytes]) -> None:
        """Initializes the inner class data with the given key.

        Note:        
            The key must be 128-bit (16 characters) in length.
        """
        key = key.encode() if isinstance(key, str) else key
        if len(key) != 16:
            raise XXTEAException("Invalid key")
        self.key = struct.unpack("IIII", key)
        assert len(self.key) == 4

    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """Encrypts and returns a block of data."""
        ldata = round(len(data) / 4)
        idata = _bytes_to_longs(data)
        if raw_xxtea(idata, ldata, self.key) != 0:
            raise XXTEAException("Cannot encrypt")
        return _longs_to_bytes(idata)

    def decrypt(self, data: Union[str, bytes]) -> bytes:
        """Decrypts and returns a block of data."""
        ldata = round(len(data) / 4)
        idata = _bytes_to_longs(data)
        if raw_xxtea(idata, -ldata, self.key) != 0:
            raise XXTEAException("Cannot decrypt")
        return _longs_to_bytes(idata).rstrip(b"\0")


metadata_crypter = XXTEA(_longs_to_bytes(CONSTANTS))


def encrypt_metadata(metadata: str) -> str:
    """Encrypts metadata to be used to log in to Amazon"""
    checksum = _generate_hex_checksum(metadata)
    object_str = f"{checksum}#{metadata}"
    object_enc = metadata_crypter.encrypt(object_str)
    object_base64 = base64.b64encode(object_enc).decode()

    return f"ECdITeCs:{object_base64}"


def decrypt_metadata(metadata: str) -> str:
    """Decrypts metadata for testing purposes only."""
    object_base64 = metadata.lstrip("ECdITeCs:")
    object_bytes = base64.b64decode(object_base64)
    object_dec = metadata_crypter.decrypt(object_bytes)
    object_str = object_dec.decode()
    checksum, metadata = object_str.split("#", 1)
    assert _generate_hex_checksum(metadata) == checksum

    return metadata


def now_to_unix_ms() -> int:
    return math.floor(datetime.now().timestamp() * 1000)


def meta_audible_app(user_agent: str, oauth_url: str) -> str:
    """
    Returns json-formatted metadata to simulate sign-in from iOS audible app.
    """

    meta_dict = {
        "start": now_to_unix_ms(),
        "interaction": {
            "keys": 0,
            "keyPressTimeIntervals": [],
            "copies": 0,
            "cuts": 0,
            "pastes": 0,
            "clicks": 0,
            "touches": 0,
            "mouseClickPositions": [],
            "keyCycles": [],
            "mouseCycles": [],
            "touchCycles": []
        },
        "version": "3.0.0",
        "lsUbid": "X39-6721012-8795219:1549849158",
        "timeZone": -6,
        "scripts": {
            "dynamicUrls": [
                ("https://images-na.ssl-images-amazon.com/images/I/"
                 "61HHaoAEflL._RC|11-BZEJ8lnL.js,01qkmZhGmAL.js,71qOHv6nKaL."
                 "js_.js?AUIClients/AudibleiOSMobileWhiteAuthSkin#mobile"),
                ("https://images-na.ssl-images-amazon.com/images/I/"
                 "21T7I7qVEeL._RC|21T1XtqIBZL.js,21WEJWRAQlL.js,31DwnWh8lFL."
                 "js,21VKEfzET-L.js,01fHQhWQYWL.js,51TfwrUQAQL.js_.js?"
                 "AUIClients/AuthenticationPortalAssets#mobile"),
                ("https://images-na.ssl-images-amazon.com/images/I/"
                 "0173Lf6yxEL.js?AUIClients/AuthenticationPortalInlineAssets"),
                ("https://images-na.ssl-images-amazon.com/images/I/"
                 "211S6hvLW6L.js?AUIClients/CVFAssets"),
                ("https://images-na.ssl-images-amazon.com/images/G/"
                 "01/x-locale/common/login/fwcim._CB454428048_.js")
            ],
            "inlineHashes": [
                -1746719145, 1334687281, -314038750, 1184642547, -137736901,
                318224283, 585973559, 1103694443, 11288800, -1611905557,
                1800521327, -1171760960, -898892073
            ],
            "elapsed": 52,
            "dynamicUrlCount": 5,
            "inlineHashesCount": 13
        },
        "plugins": "unknown||320-568-548-32-*-*-*",
        "dupedPlugins": "unknown||320-568-548-32-*-*-*",
        "screenInfo": "320-568-548-32-*-*-*",
        "capabilities": {
            "js": {
                "audio": True,
                "geolocation": True,
                "localStorage": "supported",
                "touch": True,
                "video": True,
                "webWorker": True
            },
            "css": {
                "textShadow": True,
                "textStroke": True,
                "boxShadow": True,
                "borderRadius": True,
                "borderImage": True,
                "opacity": True,
                "transform": True,
                "transition": True
            },
            "elapsed": 1
        },
        "referrer": "",
        "userAgent": user_agent,
        "location": oauth_url,
        "webDriver": None,
        "history": {
            "length": 1
        },
        "gpu": {
            "vendor": "Apple Inc.",
            "model": "Apple A9 GPU",
            "extensions": []
        },
        "math": {
            "tan": "-1.4214488238747243",
            "sin": "0.8178819121159085",
            "cos": "-0.5753861119575491"
        },
        "performance": {
            "timing": {
                "navigationStart": now_to_unix_ms(),
                "unloadEventStart": 0,
                "unloadEventEnd": 0,
                "redirectStart": 0,
                "redirectEnd": 0,
                "fetchStart": now_to_unix_ms(),
                "domainLookupStart": now_to_unix_ms(),
                "domainLookupEnd": now_to_unix_ms(),
                "connectStart": now_to_unix_ms(),
                "connectEnd": now_to_unix_ms(),
                "secureConnectionStart": now_to_unix_ms(),
                "requestStart": now_to_unix_ms(),
                "responseStart": now_to_unix_ms(),
                "responseEnd": now_to_unix_ms(),
                "domLoading": now_to_unix_ms(),
                "domInteractive": now_to_unix_ms(),
                "domContentLoadedEventStart": now_to_unix_ms(),
                "domContentLoadedEventEnd": now_to_unix_ms(),
                "domComplete": now_to_unix_ms(),
                "loadEventStart": now_to_unix_ms(),
                "loadEventEnd": now_to_unix_ms()
            }
        },
        "end": now_to_unix_ms(),
        "timeToSubmit": 108873,
        "form": {
            "email": {
                "keys": 0,
                "keyPressTimeIntervals": [],
                "copies": 0,
                "cuts": 0,
                "pastes": 0,
                "clicks": 0,
                "touches": 0,
                "mouseClickPositions": [],
                "keyCycles": [],
                "mouseCycles": [],
                "touchCycles": [],
                "width": 290,
                "height": 43,
                "checksum": "C860E86B",
                "time": 12773,
                "autocomplete": False,
                "prefilled": False
            },
            "password": {
                "keys": 0,
                "keyPressTimeIntervals": [],
                "copies": 0,
                "cuts": 0,
                "pastes": 0,
                "clicks": 0,
                "touches": 0,
                "mouseClickPositions": [],
                "keyCycles": [],
                "mouseCycles": [],
                "touchCycles": [],
                "width": 290,
                "height": 43,
                "time": 10353,
                "autocomplete": False,
                "prefilled": False
            }
        },
        "canvas": {
            "hash": -373378155,
            "emailHash": -1447130560,
            "histogramBins": []
        },
        "token": None,
        "errors": [],
        "metrics": [
            {"n": "fwcim-mercury-collector", "t": 0},
            {"n": "fwcim-instant-collector", "t": 0},
            {"n": "fwcim-element-telemetry-collector", "t": 2},
            {"n": "fwcim-script-version-collector", "t": 0},
            {"n": "fwcim-local-storage-identifier-collector", "t": 0},
            {"n": "fwcim-timezone-collector", "t": 0},
            {"n": "fwcim-script-collector", "t": 1},
            {"n": "fwcim-plugin-collector", "t": 0},
            {"n": "fwcim-capability-collector", "t": 1},
            {"n": "fwcim-browser-collector", "t": 0},
            {"n": "fwcim-history-collector", "t": 0},
            {"n": "fwcim-gpu-collector", "t": 1},
            {"n": "fwcim-battery-collector", "t": 0},
            {"n": "fwcim-dnt-collector", "t": 0},
            {"n": "fwcim-math-fingerprint-collector", "t": 0},
            {"n": "fwcim-performance-collector", "t": 0},
            {"n": "fwcim-timer-collector", "t": 0},
            {"n": "fwcim-time-to-submit-collector", "t": 0},
            {"n": "fwcim-form-input-telemetry-collector", "t": 4},
            {"n": "fwcim-canvas-collector", "t": 2},
            {"n": "fwcim-captcha-telemetry-collector", "t": 0},
            {"n": "fwcim-proof-of-work-collector", "t": 1},
            {"n": "fwcim-ubf-collector", "t": 0},
            {"n": "fwcim-timer-collector", "t": 0}
        ]
    }
    return json.dumps(meta_dict, separators=(',', ':'))
