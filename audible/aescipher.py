import base64
from hashlib import sha256 as SHA256
import hmac as HMAC
import json
import logging
import os
import pathlib
import struct
from typing import Dict, Tuple, Union

from pbkdf2 import PBKDF2
from pyaes import AESModeOfOperationCBC, Encrypter, Decrypter


logger = logging.getLogger('audible.aescipher')


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

        return {
            "salt": base64.b64encode(salt).decode("utf-8"),
            "iv": base64.b64encode(iv).decode("utf-8"),
            "ciphertext": base64.b64encode(encrypted_data).decode("utf-8"),
            "info": 'base64-encoded AES-CBC-256 of JSON object'
        }

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


def detect_file_encryption(filename: Union[pathlib.Path, pathlib.WindowsPath]):
    file = filename.read_bytes()
    try:
        file = json.loads(file)
        if "adp_token" in file:
            return False
        elif "ciphertext" in file:
            return "json"
    except UnicodeDecodeError:
        return "bytes"


def remove_file_encryption(source, target, password, **kwargs):
    encryption = detect_file_encryption(source)
    if encryption:
        source_file = pathlib.Path(source)
        crypter = AESCipher(password, **kwargs)
        decrypted = crypter.from_file(source_file, encryption=encryption)
        pathlib.Path(target).write_text(decrypted)
    else:
        raise Exception("file is not encrypted")
