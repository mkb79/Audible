# Audible

[![image](https://img.shields.io/pypi/v/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/l/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/pyversions/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/status/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/wheel/audible.svg)](https://pypi.org/project/audible/)
[![Travis](https://img.shields.io/travis/mkb79/audible/master.svg?logo=travis)](https://travis-ci.org/mkb79/audible)
[![CodeFactor](https://www.codefactor.io/repository/github/mkb79/audible/badge)](https://www.codefactor.io/repository/github/mkb79/audible)
[![image](https://img.shields.io/pypi/dm/audible.svg)](https://pypi.org/project/audible/)

**Audible is a Python low-level interface to communicate with the non-publicly 
[Audible](https://en.wikipedia.org/wiki/Audible_(service)) API.** 

It enables Python developers to create there own Audible services. 
Asynchronous communication with the Audible API is supported.

For a basic command line interface take a look at my 
[audible-cli](https://github.com/mkb79/audible-cli) package. This package 
supports:

- downloading audiobooks (aax/aaxc), cover, PDF and chapter files
- export library to [csv](https://en.wikipedia.org/wiki/Comma-separated_values)
  files
- get activation bytes
- add own plugin commands

## Requirements

- Python >= 3.6
- depends on following packages:
	- beautifulsoup4
	- httpx
	- pbkdf2
	- Pillow
	- pyaes
	- rsa

## Installation

`pip install audible`

## Read the Doc

The documentation can be found at [Read the Docs](https://audible.readthedocs.io/en/latest)
