import logging
import os


logger = logging.getLogger(__name__)


has_pycryptodomex = False
try:
    if "DISABLE_PYCRYPTODOMEX" in os.environ:
        msg = "pycryptodomex is disabled"
        logger.debug(msg)
        raise ImportError(msg)
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Signature import pkcs1_15
    from Cryptodome.Hash import SHA256
    has_pycryptodomex = True
    logger.debug("using pycryptodomex module for rsa")
except ImportError:
    import rsa
    logger.debug("using rsa module for rsa")


if has_pycryptodomex:
    import_key = RSA.import_key

    def pkcs1_sha256_sign(private_key, message):
        if isinstance(message, str):
            message = message.encode()
        h = SHA256.new(message)
        signature = pkcs1_15.new(private_key).sign(h)
        return signature
else:
    def import_key(external_key):
        if isinstance(external_key, str):
            external_key = external_key.encode("utf-8")
        return rsa.PrivateKey.load_pkcs1(external_key)

    def pkcs1_sha256_sign(private_key, message):
        if isinstance(message, str):
            message = message.encode()
        signature = rsa.pkcs1.sign(message, private_key, "SHA-256")
        return signature
