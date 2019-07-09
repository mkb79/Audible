import base64
import binascii
import ctypes
from datetime import datetime
import logging
import math


_crypto_logger = logging.getLogger('audible.crypto')


def encrypt_metadata(metadata: str) -> str:
    """
    Encrypts metadata to be used to log in to amazon.

    """
    checksum = binascii.crc32(metadata.encode()) & 0xffffffff
    checksum = checksum.to_bytes(4, byteorder='big').hex().upper()

    object_bytes = f"{checksum}#{metadata}".encode()

    temp2 = []
    for i in range(0, len(object_bytes), 4):
        data = int.from_bytes(object_bytes[i:i+4], 'little')
        temp2.append(data)

    wrap_constant = 2654435769
    constants = [1888420705, 2576816180, 2347232058, 874813317]

    rounds = math.ceil(len(object_bytes) / 4)
    minor_rounds = math.floor(6 + (52 / rounds))
    first = temp2[0]
    last = temp2[rounds - 1]

    inner_roll = 0
    while minor_rounds > 0:
        minor_rounds -= 1

        inner_roll += wrap_constant
        inner_variable = inner_roll >> 2 & 3

        for i in range(rounds):
            first = temp2[(i + 1) % rounds]
            temp2[i] += ((last >> 5 ^ first << 2)
                         + (first >> 3 ^ last << 4) ^ (inner_roll ^ first)
                         + (constants[i & 3 ^ inner_variable] ^ last))
            temp2[i] = ctypes.c_uint32(temp2[i]).value
            last = temp2[i]

    final_round = []
    for i in range(rounds):
        data2 = temp2[i].to_bytes(4, 'little')
        final_round.append(data2)

    final_round = b"".join(final_round)
    base64_encoded = base64.standard_b64encode(final_round)

    final = f"ECdITeCs:{base64_encoded.decode()}"

    return final


def decrypt_metadata(metadata: str) -> str:
    """Decrypt metadata. For testing purposes only."""
    metadata = metadata.lstrip("ECdITeCs:")

    final_round = base64.b64decode(metadata)
    temp2 = []

    for i in range(0, len(final_round), 4):
        data = int.from_bytes(final_round[i:i+4], 'little')
        temp2.append(data)

    rounds = len(temp2)
    minor_rounds = math.floor(6 + (52 / rounds))

    wrap_constant = 2654435769
    constants = [1888420705, 2576816180, 2347232058, 874813317]

    inner_roll = 0
    inner_variable = 0

    for _ in range(minor_rounds + 1):
        inner_roll += wrap_constant
        inner_variable = inner_roll >> 2 & 3

    while minor_rounds > 0:
        minor_rounds -= 1

        inner_roll -= wrap_constant
        inner_variable = inner_roll >> 2 & 3

        for i in range(rounds):
            i = rounds - i - 1

            first = temp2[(i + 1) % rounds]
            last = temp2[(i - 1) % rounds]

            temp2[i] -= ((last >> 5 ^ first << 2)
                         + (first >> 3 ^ last << 4) ^ (inner_roll ^ first)
                         + (constants[i & 3 ^ inner_variable] ^ last))
            temp2[i] = ctypes.c_uint32(temp2[i]).value
            last = temp2[i]

    object_bytes = []
    for block in temp2:
        for align in {0, 8, 16, 24}:
            if block >> align & 255 != 0:
                object_bytes.append(chr(block >> align & 255))

    object_bytes = "".join(object_bytes)

    return object_bytes[9:]


def now_to_unix_ms() -> int:
    return math.floor(datetime.now().timestamp()*1000)


def meta_audible_app(user_agent: str, oauth_url: str) -> str:
    """Returns plaintext metadata to simulate sign-in from iOS audible app."""

    return f'{{"start":{now_to_unix_ms()},"interaction":{{"keys":0,"keyPressTimeIntervals":[],"copies":0,"cuts":0,"pastes":0,"clicks":0,"touches":0,"mouseClickPositions":[],"keyCycles":[],"mouseCycles":[],"touchCycles":[]}},"version":"3.0.0","lsUbid":"X39-6721012-8795219:1549849158","timeZone":-6,"scripts":{{"dynamicUrls":["https://images-na.ssl-images-amazon.com/images/I/61HHaoAEflL._RC|11-BZEJ8lnL.js,01qkmZhGmAL.js,71qOHv6nKaL.js_.js?AUIClients/AudibleiOSMobileWhiteAuthSkin#mobile","https://images-na.ssl-images-amazon.com/images/I/21T7I7qVEeL._RC|21T1XtqIBZL.js,21WEJWRAQlL.js,31DwnWh8lFL.js,21VKEfzET-L.js,01fHQhWQYWL.js,51TfwrUQAQL.js_.js?AUIClients/AuthenticationPortalAssets#mobile","https://images-na.ssl-images-amazon.com/images/I/0173Lf6yxEL.js?AUIClients/AuthenticationPortalInlineAssets","https://images-na.ssl-images-amazon.com/images/I/211S6hvLW6L.js?AUIClients/CVFAssets","https://images-na.ssl-images-amazon.com/images/G/01/x-locale/common/login/fwcim._CB454428048_.js"],"inlineHashes":[-1746719145,1334687281,-314038750,1184642547,-137736901,318224283,585973559,1103694443,11288800,-1611905557,1800521327,-1171760960,-898892073],"elapsed":52,"dynamicUrlCount":5,"inlineHashesCount":13}},"plugins":"unknown||320-568-548-32-*-*-*","dupedPlugins":"unknown||320-568-548-32-*-*-*","screenInfo":"320-568-548-32-*-*-*","capabilities":{{"js":{{"audio":true,"geolocation":true,"localStorage":"supported","touch":true,"video":true,"webWorker":true}},"css":{{"textShadow":true,"textStroke":true,"boxShadow":true,"borderRadius":true,"borderImage":true,"opacity":true,"transform":true,"transition":true}},"elapsed":1}},"referrer":"","userAgent":"{user_agent}","location":"{oauth_url}","webDriver":null,"history":{{"length":1}},"gpu":{{"vendor":"Apple Inc.","model":"Apple A9 GPU","extensions":[]}},"math":{{"tan":"-1.4214488238747243","sin":"0.8178819121159085","cos":"-0.5753861119575491"}},"performance":{{"timing":{{"navigationStart":{now_to_unix_ms()},"unloadEventStart":0,"unloadEventEnd":0,"redirectStart":0,"redirectEnd":0,"fetchStart":{now_to_unix_ms()},"domainLookupStart":{now_to_unix_ms()},"domainLookupEnd":{now_to_unix_ms()},"connectStart":{now_to_unix_ms()},"connectEnd":{now_to_unix_ms()},"secureConnectionStart":{now_to_unix_ms()},"requestStart":{now_to_unix_ms()},"responseStart":{now_to_unix_ms()},"responseEnd":{now_to_unix_ms()},"domLoading":{now_to_unix_ms()},"domInteractive":{now_to_unix_ms()},"domContentLoadedEventStart":{now_to_unix_ms()},"domContentLoadedEventEnd":{now_to_unix_ms()},"domComplete":{now_to_unix_ms()},"loadEventStart":{now_to_unix_ms()},"loadEventEnd":{now_to_unix_ms()}}}}},"end":{now_to_unix_ms()},"timeToSubmit":108873,"form":{{"email":{{"keys":0,"keyPressTimeIntervals":[],"copies":0,"cuts":0,"pastes":0,"clicks":0,"touches":0,"mouseClickPositions":[],"keyCycles":[],"mouseCycles":[],"touchCycles":[],"width":290,"height":43,"checksum":"C860E86B","time":12773,"autocomplete":false,"prefilled":false}},"password":{{"keys":0,"keyPressTimeIntervals":[],"copies":0,"cuts":0,"pastes":0,"clicks":0,"touches":0,"mouseClickPositions":[],"keyCycles":[],"mouseCycles":[],"touchCycles":[],"width":290,"height":43,"time":10353,"autocomplete":false,"prefilled":false}}}},"canvas":{{"hash":-373378155,"emailHash":-1447130560,"histogramBins":[]}},"token":null,"errors":[],"metrics":[{{"n":"fwcim-mercury-collector","t":0}},{{"n":"fwcim-instant-collector","t":0}},{{"n":"fwcim-element-telemetry-collector","t":2}},{{"n":"fwcim-script-version-collector","t":0}},{{"n":"fwcim-local-storage-identifier-collector","t":0}},{{"n":"fwcim-timezone-collector","t":0}},{{"n":"fwcim-script-collector","t":1}},{{"n":"fwcim-plugin-collector","t":0}},{{"n":"fwcim-capability-collector","t":1}},{{"n":"fwcim-browser-collector","t":0}},{{"n":"fwcim-history-collector","t":0}},{{"n":"fwcim-gpu-collector","t":1}},{{"n":"fwcim-battery-collector","t":0}},{{"n":"fwcim-dnt-collector","t":0}},{{"n":"fwcim-math-fingerprint-collector","t":0}},{{"n":"fwcim-performance-collector","t":0}},{{"n":"fwcim-timer-collector","t":0}},{{"n":"fwcim-time-to-submit-collector","t":0}},{{"n":"fwcim-form-input-telemetry-collector","t":4}},{{"n":"fwcim-canvas-collector","t":2}},{{"n":"fwcim-captcha-telemetry-collector","t":0}},{{"n":"fwcim-proof-of-work-collector","t":1}},{{"n":"fwcim-ubf-collector","t":0}},{{"n":"fwcim-timer-collector","t":0}}]}}'

