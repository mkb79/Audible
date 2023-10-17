import base64
import hmac
import json
import logging
import os
import pathlib
import re
import struct
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal

from pbkdf2 import PBKDF2  # type: ignore[import-untyped]
from pyaes import (  # type: ignore[import-untyped]
    AESModeOfOperationCBC,
    Decrypter,
    Encrypter,
)


if TYPE_CHECKING:
    import audible


logger = logging.getLogger("audible.aescipher")

BLOCK_SIZE: int = 16  # the AES block size


def aes_cbc_encrypt(
    key: bytes, iv: bytes, data: str, padding: str = "default"
) -> bytes:
    """Encrypts data in cipher block chaining mode of operation.

    Args:
        key: The AES key.
        iv: The initialization vector.
        data: The data to encrypt.
        padding: Can be ``default`` or ``none`` (Default: default)

    Returns:
        The encrypted data.
    """
    encrypter = Encrypter(AESModeOfOperationCBC(key, iv), padding=padding)
    encrypted: bytes = encrypter.feed(data) + encrypter.feed()
    return encrypted


def aes_cbc_decrypt(
    key: bytes, iv: bytes, encrypted_data: bytes, padding: str = "default"
) -> str:
    """Decrypts data encrypted in cipher block chaining mode of operation.

    Args:
        key: The AES key used at encryption.
        iv: The initialization vector used at encryption.
        encrypted_data: The encrypted data to decrypt.
        padding: Can be ``default`` or ``none`` (Default: default)

    Returns:
        The decrypted data.
    """
    decrypter = Decrypter(AESModeOfOperationCBC(key, iv), padding=padding)
    decrypted: bytes = decrypter.feed(encrypted_data) + decrypter.feed()
    return decrypted.decode("utf-8")


def create_salt(salt_marker: bytes, kdf_iterations: int) -> tuple[bytes, bytes]:
    """Creates the header and salt for the :func:`derive_from_pbkdf2` function.

    The header consist of the number of KDF iterations encoded as a big-endian
    word bytes wrapped by ``salt_marker`` on both sides.
    The random salt has a length of 16 bytes (the AES block size) minus the
    length of the salt header.
    """
    header = salt_marker + struct.pack(">H", kdf_iterations) + salt_marker
    salt = os.urandom(BLOCK_SIZE - len(header))
    return header, salt


def pack_salt(header: bytes, salt: bytes) -> bytes:
    """Combines the header and salt created by :func:`create_salt` function."""
    return header + salt


def unpack_salt(packed_salt: bytes, salt_marker: bytes) -> tuple[bytes, int]:
    """Unpack salt and kdf_iterations from previous created and packed salt."""
    mlen = len(salt_marker)
    hlen = mlen * 2 + 2

    if not (
        packed_salt[:mlen] == salt_marker
        and packed_salt[mlen + 2 : hlen] == salt_marker
    ):
        raise ValueError("Check salt_marker.")

    kdf_iterations = struct.unpack(">H", packed_salt[mlen : mlen + 2])[0]
    salt = packed_salt[hlen:]
    return salt, kdf_iterations


def derive_from_pbkdf2(  # type: ignore[no-untyped-def]
    password: str, *, key_size: int, salt: bytes, kdf_iterations: int, hashmod, mac
) -> bytes:
    """Creates an AES key with the :class:`PBKDF2` key derivation class."""
    kdf = PBKDF2(password, salt, min(kdf_iterations, 65535), hashmod, mac)
    key: bytes = kdf.read(key_size)
    return key


class AESCipher:
    """Encrypt/Decrypt data using password to generate key.

    The encryption algorithm used is symmetric AES in cipher-block chaining
    (CBC) mode.

    The key is derived via the PBKDF2 key derivation function (KDF) from the
    password and a random salt of 16 bytes (the AES block size) minus the
    length of the salt header (see below).
    The hash function used by PBKDF2 is SHA256 per default. You can pass a
    different hash function module via the ``hashmod`` argument. The module
    must adhere to the Python API for Cryptographic Hash Functions (PEP 247).
    PBKDF2 uses a number of iterations of the hash function to derive the key,
    which can be set via the ``kdf_iterations`` keyword argument. The default
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

    Attributes:
        password: The password for encryption/decryption.
        key_size: The size of the key. Can be ``16``, ``24`` or ``32``
            (Default: 32).
        salt_marker: The salt marker with max. length of 6 bytes (Default: $).
        kdf_iterations: The number of iterations of the hash function to
            derive the key (Default: 1000).
        hashmod: The hash method to use (Default: sha256).
        mac: The mac module to use (Default: hmac).

    Args:
        password: The password for encryption/decryption.
        key_size: The size of the key. Can be ``16``, ``24`` or ``32``
            (Default: 32).
        salt_marker: The salt marker with max. length of 6 bytes (Default: $).
        kdf_iterations: The number of iterations of the hash function to
            derive the key (Default: 1000).
        hashmod: The hash method to use (Default: sha256).
        mac: The mac module to use (Default: hmac).

    Raises:
        ValueError: If `salt_marker` is not one to six bytes long.
        ValueError: If `kdf_iterations` is greater than 65535.
        TypeError: If type of `salt_marker` is not bytes.
    """

    def __init__(  # type: ignore[no-untyped-def]
        self,
        password: str,
        *,
        key_size: int = 32,
        salt_marker: bytes = b"$",
        kdf_iterations: int = 1000,
        hashmod=sha256,
        mac=hmac
    ) -> None:
        if not 1 <= len(salt_marker) <= 6:
            raise ValueError("The salt_marker must be one to six bytes long.")

        if not isinstance(salt_marker, bytes):
            raise TypeError("salt_marker must be a bytes instance.")

        if kdf_iterations >= 65536:
            raise ValueError("kdf_iterations must be <= 65535.")

        self.password = password
        self.key_size = key_size
        self.hashmod = hashmod
        self.mac = mac
        self.salt_marker = salt_marker
        self.kdf_iterations = kdf_iterations

    def _encrypt(self, data: str) -> tuple[bytes, bytes, bytes]:
        header, salt = create_salt(self.salt_marker, self.kdf_iterations)
        key = derive_from_pbkdf2(
            password=self.password,
            key_size=self.key_size,
            salt=salt,
            kdf_iterations=self.kdf_iterations,
            hashmod=self.hashmod,
            mac=self.mac,
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
            mac=self.mac,
        )
        return aes_cbc_decrypt(key, iv, encrypted_data)

    def to_dict(self, data: str) -> dict[str, str]:
        """Encrypts data in dict style.

        The output dict contains the base64 encoded (packed) salt, iv and
        ciphertext key/value pairs and an info key/value pair with additional
        encryption information.

        Args:
            data: The data to encrypt.

        Returns:
            The encrypted data in dict style.
        """
        salt, iv, encrypted_data = self._encrypt(data)

        return {
            "salt": base64.b64encode(salt).decode("utf-8"),
            "iv": base64.b64encode(iv).decode("utf-8"),
            "ciphertext": base64.b64encode(encrypted_data).decode("utf-8"),
            "info": "base64-encoded AES-CBC-256 of JSON object",
        }

    def from_dict(self, data: dict[str, str]) -> str:
        """Decrypts data previously encrypted with :meth:`AESCipher.to_dict`.

        Args:
            data: The encrypted data in json style.

        Returns:
            The decrypted data.
        """
        salt = base64.b64decode(data["salt"])
        iv = base64.b64decode(data["iv"])
        encrypted_data = base64.b64decode(data["ciphertext"])
        return self._decrypt(salt, iv, encrypted_data)

    def to_bytes(self, data: str) -> bytes:
        """Encrypts data in bytes style.

        The output bytes contains the (packed) salt, iv and ciphertext.

        Args:
            data: The data to encrypt.

        Returns:
            The encrypted data in dict style.
        """
        salt, iv, encrypted_data = self._encrypt(data)
        return salt + iv + encrypted_data

    def from_bytes(self, data: bytes) -> str:
        """Decrypts data previously encrypted with :meth:`AESCipher.to_bytes`.

        Args:
            data: The encrypted data in bytes style.

        Returns:
            The decrypted data.
        """
        bs = BLOCK_SIZE
        salt = data[:bs]
        iv = data[bs : 2 * bs]
        encrypted_data = data[2 * bs :]
        return self._decrypt(salt, iv, encrypted_data)

    def to_file(
        self,
        data: str,
        filename: pathlib.Path,
        encryption: str = "json",
        indent: int = 4,
    ) -> None:
        """Encrypts and saves data to given file.

        Args:
            data: The data to encrypt.
            filename: The name of the file to save the data to.
            encryption: The encryption style to use. Can be ``json`` or
                ``bytes`` (Default: json).
            indent: The indention level when saving in json style
                (Default: 4).

        Raises:
            ValueError: If `encryption` is not ``json`` or ``bytes``.
        """
        if encryption == "json":
            encrypted_dict = self.to_dict(data)
            data_json = json.dumps(encrypted_dict, indent=indent)
            filename.write_text(data_json)

        elif encryption == "bytes":
            encrypted_data = self.to_bytes(data)
            filename.write_bytes(encrypted_data)

        else:
            raise ValueError('encryption must be "json" or "bytes"..')

    def from_file(self, filename: pathlib.Path, encryption: str = "json") -> str:
        """Loads and decrypts data from given file.

        Args:
            filename: The name of the file to load the data from.
            encryption: The encryption style which where used. Can be ``json``
                or ``bytes`` (Default: json).

        Returns:
            The decrypted data.

        Raises:
            ValueError: If `encryption` is not ``json`` or ``bytes``.
        """
        if encryption == "json":
            encrypted_json = filename.read_text()
            encrypted_dict = json.loads(encrypted_json)
            return self.from_dict(encrypted_dict)

        if encryption == "bytes":
            encrypted_data = filename.read_bytes()
            return self.from_bytes(encrypted_data)

        raise ValueError('encryption must be "json" or "bytes".')


def detect_file_encryption(
    filename: pathlib.Path,
) -> Literal[False, "json", "bytes"] | None:
    """Detect the encryption format from an authentication file.

    Args:
        filename: The name for the authentication file.

    Returns:
        ``False`` if file is not encrypted otherwise the encryption format.
    """
    file = filename.read_bytes()
    encryption: Literal[False, "json", "bytes"] | None = None

    try:
        file_json = json.loads(file)
        if "adp_token" in file_json:
            encryption = False
        elif "ciphertext" in file_json:
            encryption = "json"
    except UnicodeDecodeError:
        encryption = "bytes"

    return encryption


def remove_file_encryption(
    source: str | pathlib.Path, target: str | pathlib.Path, password: str, **kwargs: Any
) -> None:
    """Removes the encryption from an authentication file.

    Please try to load the authentication file with
    :meth:`audible.Authenticator.from_file` and save the authentication data
    as a unencrypted file first. Use this function as fallback if you ran into
    any error.

    Args:
        source: The encrypted authentication file.
        target: The filename for the decrypted file.
        password: The password for the encrypted authentication file.
        **kwargs: keyword args supported by :class:`AESCipher`

    Raises:
        ValueError: If ``source`` is not encrypted.
    """
    source_file = pathlib.Path(source)
    encryption = detect_file_encryption(source_file)

    if not encryption:
        raise ValueError("file is not encrypted")

    crypter = AESCipher(password, **kwargs)
    decrypted = crypter.from_file(source_file, encryption=encryption)
    pathlib.Path(target).write_text(decrypted)


def _decrypt_voucher(
    device_serial_number: str,
    customer_id: str,
    device_type: str,
    asin: str,
    voucher: str,
) -> dict[str, Any]:
    # https://github.com/mkb79/Audible/issues/3#issuecomment-705262614
    buf_str = device_type + device_serial_number + customer_id + asin
    buf = buf_str.encode("ascii")
    digest = sha256(buf).digest()
    key = digest[0:16]
    iv = digest[16:]

    # decrypt "voucher" using AES in CBC mode with no padding
    b64d_voucher = base64.b64decode(voucher)
    plaintext = aes_cbc_decrypt(key, iv, b64d_voucher, padding="none").rstrip("\x00")

    try:
        voucher_dict: dict[str, Any] = json.loads(plaintext)
        return voucher_dict
    except json.JSONDecodeError:
        fmt = r"^{\"key\":\"(?P<key>.*?)\",\"iv\":\"(?P<iv>.*?)\","
        match = re.match(fmt, plaintext)
        if match is None:
            raise Exception("Failed to parse voucher.") from None
        return match.groupdict()


def decrypt_voucher_from_licenserequest(
    auth: "audible.Authenticator", license_response: dict[str, Any]
) -> dict[str, Any]:
    """Decrypt the voucher from license request response.

    Args:
        auth: The Authenticator.
        license_response: The response content from a
            :http:post:`/1.0/content/(string:asin)/licenserequest` request.

    Returns:
        The decrypted license voucher with needed key and iv.

    Raises:
        Exception: If device info or customer info data is missing.

    Note:
        A device registration is needed to use the auth instance for a
        license request and to obtain the needed device data
    """
    # device data
    device_info = auth.device_info
    if device_info is None:
        raise Exception("Device info data is missing.")
    device_serial_number = device_info["device_serial_number"]
    device_type = device_info["device_type"]

    # user data
    customer_info = auth.customer_info
    if customer_info is None:
        raise Exception("Customer info data is missing.")
    customer_id = customer_info["user_id"]

    # book specific data
    asin = license_response["content_license"]["asin"]
    encrypted_voucher = license_response["content_license"]["license_response"]

    return _decrypt_voucher(
        device_serial_number=device_serial_number,
        customer_id=customer_id,
        device_type=device_type,
        asin=asin,
        voucher=encrypted_voucher,
    )
