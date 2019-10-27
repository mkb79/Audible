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

BLOCK_SIZE = 16


def aes_cbc_encrypt(key: bytes, iv: bytes, data: str) -> bytes:
    encrypter = Encrypter(AESModeOfOperationCBC(key, iv))
    encrypted = encrypter.feed(data) + encrypter.feed()
    return encrypted


def aes_cbc_decrypt(key: bytes, iv: bytes, encrypted_data: bytes) -> str:
    decrypter = Decrypter(AESModeOfOperationCBC(key, iv))
    decrypted = decrypter.feed(encrypted_data) + decrypter.feed()
    return decrypted.decode("utf-8")


def create_salt(salt_marker: bytes, kdf_iterations: int):
    header = (salt_marker + struct.pack('>H', kdf_iterations) + salt_marker)
    salt = os.urandom(BLOCK_SIZE - len(header))
    return header, salt


def pack_salt(header, unpacked_salt):
    return (header+unpacked_salt)


def unpack_salt(packed_salt, salt_marker):
    mlen = len(salt_marker)
    hlen = mlen * 2 + 2

    if (packed_salt[:mlen] == salt_marker and
            packed_salt[mlen + 2:hlen] == salt_marker):
        kdf_iterations = struct.unpack('>H', packed_salt[mlen:mlen + 2])[0]
        salt = packed_salt[hlen:]
        return salt, kdf_iterations
    else:
        raise ValueError("Check salt_marker.")


def derive_from_pbkdf2(password: str, *, key_size: int, salt: bytes,
                       kdf_iterations: int, hashmod, mac):

    kdf = PBKDF2(password, salt, min(kdf_iterations, 65535), hashmod, mac)
    return kdf.read(key_size)


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
        header, salt = create_salt(self.salt_marker, self.kdf_iterations)
        key = derive_from_pbkdf2(
            password=self.password,
            key_size=self.key_size,
            salt=salt,
            kdf_iterations=self.kdf_iterations,
            hashmod=self.hashmod,
            mac=self.mac
        )
        iv = os.urandom(BLOCK_SIZE)
        encrypted_data = aes_cbc_encrypt(key, iv, data)
        return pack_salt(header, salt), iv, encrypted_data

    def _decrypt(self, salt: bytes, iv: bytes, encrypted_data: bytes) -> str:
        try:
            salt, kdf_iterations = unpack_salt(salt, self.salt_marker)
        except ValueError:
            kdf_iterations = self.kdf_iterations
        key = derive_from_pbkdf2(
            password=self.password,
            key_size=self.key_size,
            salt=salt,
            kdf_iterations=kdf_iterations,
            hashmod=self.hashmod,
            mac=self.mac
        )
        return aes_cbc_decrypt(key, iv, encrypted_data)

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
        bs = BLOCK_SIZE
        salt = data[:bs]
        iv = data[bs:2*bs]
        encrypted_data = data[2*bs:]

        return self._decrypt(salt, iv, encrypted_data)

    def to_file(self, data: str,
                filename: Union[pathlib.Path, pathlib.WindowsPath],
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
