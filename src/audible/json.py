import logging
import os

from httpx._utils import guess_json_utf


logger = logging.getLogger(__name__)

has_ujson = False
try:
    if "DISABLE_UJSON" in os.environ:
        msg = "ujson is disabled"
        logger.debug(msg)
        raise ImportError(msg)
    import ujson as jsonlib
    has_ujson = True
    logger.debug("using ujson module for json")
except ImportError:
    import json as jsonlib
    logger.debug("using json module for json")


JSONDecodeError = jsonlib.JSONDecodeError


def dump(*args, **kwargs):
    return jsonlib.dump(*args, **kwargs)


def load(*args, **kwargs):
    return jsonlib.load(*args, **kwargs)


def loads(data):
    return jsonlib.loads(data)


def dumps(data):
    return jsonlib.dumps(data, ensure_ascii=False)


if has_ujson:
    def response_to_json(resp):
        if resp.charset_encoding is None and resp.content and len(resp.content) > 3:
            encoding = guess_json_utf(resp.content)
            if encoding is not None:
                return loads(resp.content.decode(encoding))
        return loads(resp.text)
else:
    def response_to_json(resp):
        return resp.json()
