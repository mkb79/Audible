"""
This module is inspired from sphinx.cmd.quickstart
"""

import pathlib
import sys
from typing import Any, Callable, Union

try:
    import readline
    if readline.__doc__ and 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
        USE_LIBEDIT = True
    else:
        readline.parse_and_bind("tab: complete")
        USE_LIBEDIT = False
except ImportError:
    USE_LIBEDIT = False

from audible.cmd.console import colorize, red

PROMPT_PREFIX = '> '

if sys.platform == 'win32':
    # On Windows, show questions as bold because of color scheme of PowerShell (refs: #5294).
    COLOR_QUESTION = 'bold'
else:
    COLOR_QUESTION = 'purple'


# function to get input from terminal -- overridden by the test suite
def term_input(prompt: str) -> str:
    if sys.platform == 'win32':
        # Important: On windows, readline is not enabled by default.  In these
        #            environment, escape sequences have been broken.  To avoid the
        #            problem, quickstart uses ``print()`` to show prompt.
        print(prompt, end='')
        return input('')
    else:
        return input(prompt)


class ValidationError(Exception):
    """Raised for validation errors."""


def is_path(x: str) -> str:
    if not pathlib.Path(x).is_dir():
        raise ValidationError("Please enter a valid path name.")
    return x


def allow_empty(x: str) -> str:
    return x


def nonempty(x: str) -> str:
    if not x:
        raise ValidationError("Please enter some text.")
    return x


def choice(*l: str) -> Callable[[str], str]:
    def val(x: str) -> str:
        if x not in l:
            raise ValidationError('Please enter one of %s.' % ', '.join(l))
        return x
    return val


def boolean(x: str) -> bool:
    if x.upper() not in ('Y', 'YES', 'N', 'NO'):
        raise ValidationError("Please enter either 'y' or 'n'.")
    return x.upper() in ('Y', 'YES')


def suffix(x: str) -> str:
    if not (x[0:1] == '.' and len(x) > 1):
        raise ValidationError("Please enter a file suffix, e.g. '.rst' or '.txt'.")
    return x


def ok(x: str) -> str:
    return x


def do_prompt(text: str, default: str = None, validator: Callable[[str], Any] = nonempty) -> Union[str, bool]:  # NOQA
    while True:
        if default is not None:
            prompt = PROMPT_PREFIX + '%s [%s]: ' % (text, default)
        else:
            prompt = PROMPT_PREFIX + text + ': '
        if USE_LIBEDIT:
            # Note: libedit has a problem for combination of ``input()`` and escape
            # sequence (see #5335).  To avoid the problem, all prompts are not colored
            # on libedit.
            pass
        else:
            prompt = colorize(COLOR_QUESTION, prompt, input_mode=True)
        x = term_input(prompt).strip()
        if default and not x:
            x = default
        try:
            x = validator(x)
        except ValidationError as err:
            print(red('* ' + str(err)))
            continue
        break
    return x
