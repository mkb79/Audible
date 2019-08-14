import base64
import binascii
from datetime import datetime
from hashlib import sha256 as SHA256
import hmac as HMAC
import json
import logging
import math
import os
import pathlib
import struct
from typing import Dict, List, Tuple, Union

from pbkdf2 import PBKDF2
from pyaes import AESModeOfOperationCBC, Encrypter, Decrypter


_crypto_logger = logging.getLogger('audible.crypto')


class AESCipher:
    """Encrypt/Decrypt data using password to generate key. The encryption
    algorithm used is symmetric AES in cipher-block chaining (CBC) mode.
    
    ``key_size`` may be 16, 24 or 32 (default).
    The key is derived via the PBKDF2 key derivation function (KDF) from the
    password and a random salt of 16 bytes (the AES block size) minus the
    length of the salt header (see below).
    The hash function used by PBKDF2 is SHA256 per default. You can pass a
    different hash function module via the ``hashmod`` argument. The module
    must adhere to the Python API for Cryptographic Hash Functions (PEP 247).
    PBKDF2 uses a number of iterations of the hash function to derive the key,
    which can be set via the ``kdf_iterations` keyword argumeent. The default
    number is 1000 and the maximum 65535.
    The header and the salt are written to the first block of the encrypted
    output (bytes mode) or written as key/value pairs (dict mode). The header
    consist of the number of KDF iterations encoded as a big-endian word bytes
    wrapped by ``salt_marker`` on both sides. With the default value of
    ``salt_marker = b'$'``, the header size is thus 4 and the salt 12 bytes.
    The salt marker must be a byte string of 1-6 bytes length.
    The last block of the encrypted output is padded with up to 16 bytes, all
    having the value of the length of the padding.
    All values in dict mode are written as base64 encoded string.
    """

    def __init__(self, password: str, *, key_size: int = 32,
                 salt_marker: bytes = b"$", kdf_iterations: int = 1000,
                 hashmod=SHA256, mac=HMAC) -> None:

        self.password = password
        self.key_size = key_size
        self.hashmod = hashmod
        self.mac = mac
        self.bs = 16
        
        if not 1 <= len(salt_marker) <= 6:
            raise ValueError('The salt_marker must be one to six bytes long.')
        elif not isinstance(salt_marker, bytes):
            raise TypeError('salt_marker must be a bytes instance.')
        else:
            self.salt_marker = salt_marker

        if kdf_iterations >= 65536:
            raise ValueError('kdf_iterations must be <= 65535.')
        else:
            self.kdf_iterations = kdf_iterations

    def _encrypt(self, data: str) -> Tuple[bytes, bytes, bytes]:
        bs = self.bs
        header = (self.salt_marker
                  + struct.pack('>H', self.kdf_iterations)
                  + self.salt_marker)
        salt = os.urandom(bs - len(header))
        kdf = PBKDF2(self.password, salt, min(self.kdf_iterations, 65535),
                     self.hashmod, self.mac)
        key = kdf.read(self.key_size)
        iv = os.urandom(bs)
        encrypter = Encrypter(AESModeOfOperationCBC(key, iv))

        encrypted = encrypter.feed(data)
        encrypted += encrypter.feed()
    
        return (header+salt), iv, encrypted

    def _decrypt(self, salt: bytes, iv: bytes, encrypted_data: bytes) -> str:
        mlen = len(self.salt_marker)
        hlen = mlen * 2 + 2
    
        if salt[:mlen] == self.salt_marker and salt[mlen + 2:hlen] == self.salt_marker:
            kdf_iterations = struct.unpack('>H', salt[mlen:mlen + 2])[0]
            salt = salt[hlen:]
        else:
            kdf_iterations = self.kdf_iterations
    
        if kdf_iterations >= 65536:
            raise ValueError('kdf_iterations must be <= 65535.')

        kdf = PBKDF2(self.password, salt, self.kdf_iterations,
                     self.hashmod, self.mac)
        key = kdf.read(self.key_size)
        decrypter = Decrypter(AESModeOfOperationCBC(key, iv))

        decrypted = decrypter.feed(encrypted_data)
        decrypted += decrypter.feed()

        return decrypted.decode("utf-8")

    def to_dict(self, data: str) -> Dict[str, str]:
        salt, iv, encrypted_data = self._encrypt(data)

        return {"salt": base64.b64encode(salt).decode("utf-8"),
                "iv": base64.b64encode(iv).decode("utf-8"),
                "ciphertext": base64.b64encode(encrypted_data).decode("utf-8"),
                "info": 'base64-encoded AES-CBC-256 of JSON object'}

    def from_dict(self, data: dict) -> str:
        salt = base64.b64decode(data["salt"])
        iv = base64.b64decode(data["iv"])
        encrypted_data = base64.b64decode(data["ciphertext"])

        return self._decrypt(salt, iv, encrypted_data)

    def to_bytes(self, data: str) -> bytes:
        salt, iv, encrypted_data = self._encrypt(data)

        return salt + iv + encrypted_data

    def from_bytes(self, data: bytes) -> str:
        bs = self.bs
        salt = data[:bs]
        iv = data[bs:2*bs]
        encrypted_data = data[2*bs:]

        return self._decrypt(salt, iv, encrypted_data)

    def to_file(self, data: str, filename: Union[pathlib.Path, pathlib.WindowsPath],
                encryption="json", indent=4):
        if encryption == "json":
            encrypted_dict = self.to_dict(data)
            data_json = json.dumps(encrypted_dict, indent=indent)
            filename.write_text(data_json)

        elif encryption == "bytes":
            encrypted_data = self.to_bytes(data)
            filename.write_bytes(encrypted_data)

        else:
            raise ValueError("encryption must be \"json\" or \"bytes\"..")

    def from_file(self, filename: Union[pathlib.Path, pathlib.WindowsPath],
                  encryption="json"):
        if encryption == "json":
            encrypted_json = filename.read_text()
            encrypted_dict = json.loads(encrypted_json)

            return self.from_dict(encrypted_dict)

        elif encryption == "bytes":
            encrypted_data = filename.read_bytes()
    
            return self.from_bytes(encrypted_data)

        else:
            raise ValueError("encryption must be \"json\" or \"bytes\".")


# constants used for encrypt/decrypt metadata
WRAP_CONSTANT = 2654435769
CONSTANTS = [1888420705, 2576816180, 2347232058, 874813317]


def _data_to_int_list(data: Union[str, bytes]) -> List[int]:
    data_bytes = data.encode() if isinstance(data, str) else data
    data_list_int = []
    for i in range(0, len(data_bytes), 4):
        data_list_int.append(int.from_bytes(data_bytes[i:i+4], "little"))

    return data_list_int


def _list_int_to_bytes(data: List[int]) -> bytearray:
    data_list = data
    data_bytes = bytearray()
    for i in data_list:
        data_bytes += i.to_bytes(4, 'little')

    return data_bytes


def _encrypt_data(data: List[int]) -> List[int]:
    temp2 = data
    rounds = len(temp2)
    minor_rounds = int(6 + (52 / rounds // 1))
    last = temp2[-1]
    inner_roll = 0

    for _ in range(minor_rounds):
        inner_roll += WRAP_CONSTANT
        inner_variable = inner_roll >> 2 & 3

        for i in range(rounds):
            first = temp2[(i + 1) % rounds]
            temp2[i] += ((last >> 5 ^ first << 2)
                     + (first >> 3 ^ last << 4) ^ (inner_roll ^ first)
                     + (CONSTANTS[i & 3 ^ inner_variable] ^ last))
            last = temp2[i] = temp2[i] & 0xffffffff

    return temp2


def _decrypt_data(data: List[int]) -> List[int]:
    temp2 = data
    rounds = len(temp2)
    minor_rounds = int(6 + (52 / rounds // 1))
    inner_roll = 0

    for _ in range(minor_rounds + 1):
        inner_roll += WRAP_CONSTANT
        inner_variable = inner_roll >> 2 & 3

    for _ in range(minor_rounds):
        inner_roll -= WRAP_CONSTANT
        inner_variable = inner_roll >> 2 & 3

        for i in range(rounds):
            i = rounds - i - 1

            first = temp2[(i + 1) % rounds]
            last = temp2[(i - 1) % rounds]

            temp2[i] -= ((last >> 5 ^ first << 2)
                         + (first >> 3 ^ last << 4) ^ (inner_roll ^ first)
                         + (CONSTANTS[i & 3 ^ inner_variable] ^ last))
            last = temp2[i] = temp2[i] & 0xffffffff

    return temp2


def _generate_hex_checksum(data: str) -> str:
    checksum_int = binascii.crc32(data.encode()) & 0xffffffff
    return checksum_int.to_bytes(4, byteorder='big').hex().upper()


def encrypt_metadata(metadata: str) -> str:
    """
    Encrypts metadata to be used to log in to amazon.

    """
    checksum = _generate_hex_checksum(metadata)

    object_str = f"{checksum}#{metadata}"

    object_list_int = _data_to_int_list(object_str)

    object_list_int_enc = _encrypt_data(object_list_int)

    object_bytes = _list_int_to_bytes(object_list_int_enc)

    object_base64 = base64.b64encode(object_bytes)

    return f"ECdITeCs:{object_base64.decode()}"


def decrypt_metadata(metadata: str) -> str:
    """Decrypt metadata. For testing purposes only."""
    object_base64 = metadata.lstrip("ECdITeCs:")

    object_bytes = base64.b64decode(object_base64)

    object_list_int = _data_to_int_list(object_bytes)

    object_list_int_dec = _decrypt_data(object_list_int)

    object_bytes = _list_int_to_bytes(object_list_int_dec).rstrip(b"\0")

    object_str = object_bytes.decode()

    checksum, metadata = object_str.split("#", 1)

    assert _generate_hex_checksum(metadata) == checksum

    return metadata


def now_to_unix_ms() -> int:
    return math.floor(datetime.now().timestamp()*1000)


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
                -1746719145,
                1334687281,
                -314038750,
                1184642547,
                -137736901,
                318224283,
                585973559,
                1103694443,
                11288800,
                -1611905557,
                1800521327,
                -1171760960,
                -898892073
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
            {
                "n": "fwcim-mercury-collector",
                "t": 0
            },
            {
                "n": "fwcim-instant-collector",
                "t": 0
            },
            {
                "n": "fwcim-element-telemetry-collector",
                "t": 2
            },
            {
                "n": "fwcim-script-version-collector",
                "t": 0
            },
            {
                "n": "fwcim-local-storage-identifier-collector",
                "t": 0
            },
            {
                "n": "fwcim-timezone-collector",
                "t": 0
            },
            {
                "n": "fwcim-script-collector",
                "t": 1
            },
            {
                "n": "fwcim-plugin-collector",
                "t": 0
            },
            {
                "n": "fwcim-capability-collector",
                "t": 1
            },
            {
                "n": "fwcim-browser-collector",
                "t": 0
            },
            {
                "n": "fwcim-history-collector",
                "t": 0
            },
            {
                "n": "fwcim-gpu-collector",
                "t": 1
            },
            {
                "n": "fwcim-battery-collector",
                "t": 0
            },
            {
                "n": "fwcim-dnt-collector",
                "t": 0
            },
            {
                "n": "fwcim-math-fingerprint-collector",
                "t": 0
            },
            {
                "n": "fwcim-performance-collector",
                "t": 0
            },
            {
                "n": "fwcim-timer-collector",
                "t": 0
            },
            {
                "n": "fwcim-time-to-submit-collector",
                "t": 0
            },
            {
                "n": "fwcim-form-input-telemetry-collector",
                "t": 4
            },
            {
                "n": "fwcim-canvas-collector",
                "t": 2
            },
            {
                "n": "fwcim-captcha-telemetry-collector",
                "t": 0
            },
            {
                "n": "fwcim-proof-of-work-collector",
                "t": 1
            },
            {
                "n": "fwcim-ubf-collector",
                "t": 0
            },
            {
                "n": "fwcim-timer-collector",
                "t": 0
            }
        ]
    }
    return json.dumps(meta_dict, separators=(',', ':'))
