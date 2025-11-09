import base64
import logging
import warnings
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from .device import BaseDevice


logger = logging.getLogger("audible.register")


def _convert_base64_der_to_pem(base64_key: str) -> str:
    """Convert Android base64-DER certificate to PEM format.

    Android returns private keys in PKCS#8 format (base64-encoded DER).
    This function decodes the PKCS#8 structure and extracts the RSA key,
    then converts it to PEM format.

    Args:
        base64_key: Base64-encoded DER certificate (Android PKCS#8 format)

    Returns:
        PEM-formatted private key string

    Raises:
        ValueError: If conversion fails
    """
    try:
        import rsa
        from pyasn1.codec.der import decoder
        from pyasn1.type import namedtype, univ

        class PrivateKeyAlgorithm(univ.Sequence):
            componentType = namedtype.NamedTypes(  # noqa: N815
                namedtype.NamedType("algorithm", univ.ObjectIdentifier()),
                namedtype.NamedType("parameters", univ.Any()),
            )

        class PrivateKeyInfo(univ.Sequence):
            componentType = namedtype.NamedTypes(  # noqa: N815
                namedtype.NamedType("version", univ.Integer()),
                namedtype.NamedType("pkalgo", PrivateKeyAlgorithm()),
                namedtype.NamedType("key", univ.OctetString()),
            )

        # Decode base64 to DER bytes
        encoded_key = base64.b64decode(base64_key)

        # Decode PKCS#8 structure
        (key_info, _) = decoder.decode(encoded_key, asn1Spec=PrivateKeyInfo())

        # Extract the octet string containing the actual RSA key
        key_octet_string = key_info["key"]

        # Load RSA key from DER format
        key = rsa.PrivateKey.load_pkcs1(key_octet_string, format="DER")

        # Save as PEM format
        return key.save_pkcs1().decode("utf-8")

    except Exception as e:
        raise ValueError(f"Failed to convert base64-DER to PEM format: {e}") from e


def register(
    authorization_code: str,
    code_verifier: bytes,
    domain: str,
    serial: str | None = None,
    with_username: bool = False,
    device: "BaseDevice | None" = None,
) -> dict[str, Any]:
    """Registers a dummy Audible device.

    .. deprecated:: v0.11.0
        Use :class:`audible.RegistrationService` instead for better testability
        and maintainability. This function is now a wrapper around the
        service class and will be removed in v0.12.0.

    Args:
        authorization_code: The code given after a successful authorization
        code_verifier: The verifier code from authorization
        domain: The top level domain of the requested Amazon server (e.g. com).
        serial: The device serial. DEPRECATED: Use device parameter instead.
        with_username: If ``True`` uses `audible` domain instead of `amazon`.
        device: The device to register. If ``None``, uses default iPhone device.

    Returns:
        Additional authentication data needed for access Audible API.

    .. versionadded:: v0.7.1
           The with_username argument
    .. versionadded:: v0.11.0
           The device argument
    .. versionchanged:: v0.11.0
           Now uses RegistrationService internally. Prefer using RegistrationService directly.
    """
    from .registration_service import register as _register_impl

    warnings.warn(
        "Importing from audible.register is deprecated and will be removed in v0.12.0. "
        "Use audible.RegistrationService instead for better testability and control.",
        DeprecationWarning,
        stacklevel=2,
    )

    return _register_impl(
        authorization_code=authorization_code,
        code_verifier=code_verifier,
        domain=domain,
        serial=serial,
        with_username=with_username,
        device=device,
    )


def deregister(
    access_token: str,
    domain: str,
    deregister_all: bool = False,
    with_username: bool = False,
) -> Any:
    """Deregister a previous registered Audible device.

    .. deprecated:: v0.11.0
        Use :class:`audible.RegistrationService` instead for better testability
        and maintainability. This function is now a wrapper around the
        service class and will be removed in v0.12.0.

    Note:
        Except of the ``access_token``, all authentication data will lose
        validation immediately.

    Args:
        access_token: The access token from the previous registered device
            which you want to deregister.
        domain: The top level domain of the requested Amazon server (e.g. com).
        deregister_all: If ``True``, deregister all Audible devices on Amazon.
        with_username: If ``True`` uses `audible` domain instead of `amazon`.

    Returns:
        The response for the deregister request. Contains errors, if some occurs.

    .. versionadded:: v0.8
           The with_username argument
    .. versionchanged:: v0.11.0
           Now uses RegistrationService internally. Prefer using RegistrationService directly.
    """
    from .registration_service import deregister as _deregister_impl

    warnings.warn(
        "Importing from audible.register is deprecated and will be removed in v0.12.0. "
        "Use audible.RegistrationService instead for better testability and control.",
        DeprecationWarning,
        stacklevel=2,
    )

    return _deregister_impl(
        access_token=access_token,
        domain=domain,
        deregister_all=deregister_all,
        with_username=with_username,
    )
