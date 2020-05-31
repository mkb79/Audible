# Audible

[![image](https://img.shields.io/pypi/v/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/l/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/pyversions/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/status/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/wheel/audible.svg)](https://pypi.org/project/audible/)
[![Travis](https://img.shields.io/travis/mkb79/audible/master.svg?logo=travis)](https://travis-ci.org/mkb79/audible)
[![image](https://img.shields.io/pypi/implementation/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/dm/audible.svg)](https://pypi.org/project/audible/)

**Sync/Async Interface for internal Audible API written in pure Python.**

Code and README are forked from omarroth‘s fantastic [audible.cr](https://github.com/omarroth/audible.cr) API written in crystal.
The whole code is written with Pythonista for iOS.

## Requirements

- Python >= 3.6
- depends on following packages:
	- aiohttp
	- beautifulsoup4
	- pbkdf2
	- Pillow
	- pyaes
	- requests
	- rsa 

## Installation

`pip install audible`

## Usage

### Basis Examples

- Retrieving API credentials

*Hint: With every LoginAuthenticator init a new audible device will be registered on amazon by default. This client needs the credentials obtained by device registration process to use sign request authentication on audible api (access token authentication are not supported at this moment by this client. Please use LoginAuthenticator only once and then save your credentials.*

*Hint: If you want to use multiple audible marketplaces, only one device registration is needed. The credentials from device registration process are valid for all audible marketplaces.*

```python
import audible

# example for US accounts
auth = audible.LoginAuthenticator(
    "EMAIL",
    "PASSWORD",
    locale="us"
)
```

- Save credentials

*Hint: locale (country) code are stored in file*

```python
auth.to_file("FILENAME", encryption=False)
```

- Load credentials from file

*Hint: uses saved locale code*

```python
auth = audible.FileAuthenticator("FILENAME")

# to specify another locale code at restore
auth = audible.FileAuthenticator(
    "FILENAME",
    locale="some other locale"
)
```

- Instantiate API with Authenticator

*Hint: the Authenticator will be stored as `auth` attribute, you can access them with `client.auth`*

```python
client = audible.AudibleAPI(auth)
```

- retrieving library from API

*Hint: with any request you get a list with response text and the raw response object*

*Hint: audibles current API version is 1.0, the Client use this version on default*

```python
library, _ = client.get(
    path="library",
    params={
        "num_results": 999,
        "response_groups": "media, sample"
    }
)
```

- change requested marketplace without instantiate new client

```python
# read Localizations for available country codes

client.switch_marketplace("us")  # switch to us marketplace
client.switch_marketplace("de")  # switch to german marketplace

```

- to specify another API version

```
library, _ = client.get(
    path="library/books",
    api_version="0.0",
    params={
        "purchaseAfterDate": "01/01/1970",
        "sortInAscendingOrder": "true"
    }
)
```

### Localizations

Currently this Client have localizations for 9 audible marketplaces built-in.

- USA (locale="us")
- Germany (locale="de")
- United Kingdom (locale="uk")
- France (locale="fr")
- Canada (locale="ca")
- Italy (locale="it")
- Australia (locale="au")
- India (locale="in")
- Japan (locale="jp")

You can provide custom locales with this code:

```python
import audible

# example for uk
custom_locale = audible.Locale(
    countryCode="uk",
    domain="co.uk",
    marketPlaceId="A2I9A3Q2GNFNGQ",
)

auth = audible.LoginAuthenticator(..., locale=custom_locale)
client = audible.AudibleAPI(auth)
```

You can try to autodetect locales like so:

```python
from audible.localization import autodetect_locale

# needs the Top Level Domain for the audible page in your country
# example for uk
custom_locale = autodetect_locale("co.uk")

# look if everything is fine
print(custom_locale)

# create Authenticator
custom_locale = audible.Locale(**custom_locale)
auth = audible.LoginAuthenticator(..., locale=custom_locale)
```


### Load and Save Credentials

#### Saved data

If you save a session following data will be stored in file:

- login_cookies
- access_token
- refresh_token
- adp_token
- device_private_key
- locale_code
- store_authentication_cookie (*new*)
- device_info (*new*)
- customer_info (*new*)
- expires

#### Unencrypted Load/Save

Credentials can be saved any time to file like so:

```python
import audible

auth = audible.LoginAuthenticator(...)
auth.to_file("FILENAME", encryption=False)

# Sometime later...
auth = audible.FileAuthenticator("FILENAME")
```

Authenticator sets the filename as the default value when loading from or save to file simply run to overwrite old file
`auth.to_file()`. No filename is needed.

#### Encrypted Load/Save

This Client supports file encryption now. The encryption
algorithm used is symmetric AES in cipher-block chaining (CBC) mode. Currently json and bytes style output are supported.
Credentials can be saved any time to encrypted file like so:

```python
import audible

auth = audible.LoginAuthenticator(...)

# save credentials in json style
auth.to_file(
    "FILENAME",
    "PASSWORD",
    encryption="json"
)

# in bytes style
auth.to_file(
    "FILENAME",
    "PASSWORD",
    encryption="bytes"
)

# Sometime later...
# load credentials
# encryption style are autodetected
auth = audible.FileAuthenticator(
    "FILENAME",
    "PASSWORD"
)
```

Authenticator sets the filename, password and encryption style as the default values when loading from or save to file simply run to overwrite old file with same password and encryption style
`auth.to_file()`. No filename is needed.

##### Advanced use of encryption/decryption:

`auth.to_file(..., **kwargs)`

`auth = audible.FileAuthenticator(..., **kwargs)`

Following arguments are possible:

- key_size (default = 32)
- salt_marker (default = b"$")
- kdf_iterations (default = 1000)
- hashmod (default = Crypto.Hash.SHA256)
    
`key_size` may be 16, 24 or 32. The key is derived via the PBKDF2 key derivation function (KDF) from the password and a random salt of 16 bytes (the AES block size) minus the length of the salt header (see below).
The hash function used by PBKDF2 is SHA256 per default. You can pass a different hash function module via the `hashmod` argument. The module must adhere to the Python API for Cryptographic Hash Functions (PEP 247).
PBKDF2 uses a number of iterations of the hash function to derive the key, which can be set via the `kdf_iterations` keyword argumeent. The default number is 1000 and the maximum 65535.
The header and the salt are written to the first block of the encrypted output (bytes mode) or written as key/value pairs (dict mode). The header consist of the number of KDF iterations encoded as a big-endian word bytes wrapped by `salt_marker` on both sides. With the default value of `salt_marker = b'$'`, the header size is thus 4 and the salt 12 bytes.
The salt marker must be a byte string of 1-6 bytes length.
The last block of the encrypted output is padded with up to 16 bytes, all having the value of the length of the padding.
In json style all values are written as base64 encoded string.

#### Remove encryption

To remove encryption from file (or save as new file):

```python
from audible.aescipher import remove_file_encryption

encrypted_file = "FILENAME"
decrypted_file = "FILENAME"
password = "PASSWORD"

remove_file_encryption(
    encrypted_file,
    decrypted_file,
    password
)
```

### CAPTCHA

Logging in currently requires answering a CAPTCHA. By default Pillow is used to show captcha and user prompt will be provided using `input`, which looks like:

```
Answer for CAPTCHA:
```

If Pillow can't display the captcha, the captcha url will be printed.

A custom callback can be provided (for example submitting the CAPTCHA to an external service), like so:

```
def custom_captcha_callback(captcha_url):
    
    # Do some things with the captcha_url ... 
    # maybe you can call webbrowser.open(captcha_url)

    return "My answer for CAPTCHA"

auth = audible.LoginAuthenticator(
    "EMAIL",
    "PASSWORD",
    locale="us",
    captcha_callback=custom_captcha_callback
)
```

### 2FA

If 2-factor-authentication by default is activated a user prompt will be provided using `input`, which looks like:

```
"OTP Code: "
```

A custom callback can be provided, like so:

```
def custom_otp_callback():
    
    # Do some things to insert otp code

    return "My answer for otp code"

auth = audible.LoginAuthenticator(
    "EMAIL",
    "PASSWORD",
    locale="us",
    otp_callback=custom_otp_callback
)
```


### Logging

In preparation of adding logging in near future I add following functions:

```python
import audible

# console logging
audible.set_console_logger("level")

# file logging
audible.set_file_logger("filename", "level")

```

Following levels will be accepted:

- debug
- info
- warn (or warning)
- error
- critical

You can use numeric levels too:

- 10 (debug)
- 20 (info)
- 30 (warn)
- 40 (error)
- 50 (critical)

### Asynchron requests

By default the AudibleAPI client requests are synchron using the requests module.

The client supports now asynchronous request using the aiohttp module. You can instantiate a async client with `client = audible.AudibleAPI(..., is_async=True)`. Example to use async client can be found in [example folder](https://github.com/mkb79/Audible/tree/developing/examples) on github repo.

## Authentication

### Informations

Clients are authenticated using OpenID. Once a client has successfully authenticated with Amazon, they are given an access token for authenticating with Audible.

### Register device

Clients authenticate with Audible using cookies from Amazon and the given access token to `/auth/register`. Clients are given an refresh token, RSA private key and adp_token.

For requests to the Audible API, requests need to be signed using the provided RSA private key and adp_token. Request signing is fairly straight-forward and uses a signed SHA256 digest. Headers look like:

```
x-adp-alg: SHA256withRSA:1.0
x-adp-signature: AAAAAAAA...:2019-02-16T00:00:01.000000000Z,
x-adp-token: {enc:...}
```

As reference for other implementations, a client **must** store a working `access_token` from a successful Amazon login in order to renew `refresh_token`, `adp_token`, etc from `/auth/register`.

### Refresh access token

An `access_token` can be renewed by making a request to `/auth/token`. `access_token`s are valid for 1 hour.
To renew access_token with client call:

```python
# refresh access_token if token already expired
# if token is valid nothing will be refreshed.
auth.refresh_token()

# to force renew of access_token if token is valid
auth.refresh_token(force=true)
```

*Hint: If you saved your session before don't forget to save again.*

### Deregister device

Refresh token, RSA private key and adp_token are valid until deregister.

To deregister a device with client call `auth.deregister_device()`

To deregister all devices with client call `auth.deregister_device(deregister_all=True)`.
This function is necessary to prevent hanging slots if you registered a device earlier but don‘t store the given credentials.
This also deregister all other devices such as a audible app on mobile devices.

## Documentation:

There is currently no publicly available documentation about the Audible API. There is a node client ([audible-api](https://github.com/willthefirst/audible/tree/master/node_modules/audible-api)) that has some endpoints documented, but does not provide information on authentication.

Luckily the Audible API is partially self-documenting, however the parameter names need to be known. Error responses will look like:

```json
{
  "message": "1 validation error detected: Value 'some_random_string123' at 'numResults' failed to satisfy constraint: Member must satisfy regular expression pattern: ^\\d+$"
}
```

Few endpoints have been fully documented, as a large amount of functionality is not testable from the app or functionality is unknown. Most calls need to be authenticated.

For `%s` substitutions the value is unknown or can be inferred from the endpoint. `/1.0/catalog/products/%s` for example requires an `asin`, as in `/1.0/catalog/products/B002V02KPU`.

Each bullet below refers to a parameter for the request with the specified method and URL.

Responses will often provide very little info without `response_groups` specified. Multiple response groups can be specified, for example: `/1.0/catalog/products/B002V02KPU?response_groups=product_plan_details,media,review_attrs`. When providing an invalid response group, the server will return an error response but will not provide information on available response groups.

### GET /0.0/library/books

#### Deprecated: Use `/1.0/library`

params:

- purchaseAfterDate: mm/dd/yyyy
- sortByColumn: [SHORT_TITLE, strTitle, DOWNLOAD_STATUS, RUNNING_TIME, sortPublishDate, SHORT_AUTHOR, sortPurchDate, DATE_AVAILABLE]
- sortInAscendingOrder: [true, false]

### GET /1.0/library

params:

- num_results: \\d+ (max: 1000)
- page: \\d+
- purchased_after: [RFC3339](https://tools.ietf.org/html/rfc3339) (e.g. `2000-01-01T00:00:00Z`)
- response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, sample, sku, series, reviews, ws4v, origin, relationships, review_attrs, categories, badge_types, category_ladders, claim_code_url, is_downloaded, is_finished, is_returnable, origin_asin, pdf_url, percent_complete, provided_review]
- sort_by: [-Author, -Length, -Narrator, -PurchaseDate, -Title, Author, Length, Narrator, PurchaseDate, Title]

### GET /1.0/library/%{asin}

params:

- response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, sample, sku, series, reviews, ws4v, origin, relationships, review_attrs, categories, badge_types, category_ladders, claim_code_url, is_downloaded, is_finished, is_returnable, origin_asin, pdf_url, percent_complete, provided_review]

### POST(?) /1.0/library/item

- asin:

### POST(?) /1.0/library/item/%s/%s

### GET /1.0/wishlist

params:

- num_results: \\d+ (max: 50)
- page: \\d+
- response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, sample, sku]
- sort_by: [-Author, -DateAdded, -Price, -Rating, -Title, Author, DateAdded, Price, Rating, Title]

### POST /1.0/wishlist

body:

- asin : String

Example request body:

```json
{
  "asin": "B002V02KPU"
}
```

Returns 201 and a `Location` to the resource.

### DELETE /1.0/wishlist/%{asin}

Returns 204 and removes the item from the wishlist using the given `asin`.

### GET /1.0/badges/progress

params:

- locale: en_US
- response_groups: brag_message
- store: Audible

### GET /1.0/badges/metadata

params:

- locale: en_US
- response_groups: all_levels_metadata

### GET /1.0/account/information

params:

- response_groups: [delinquency_status, customer_benefits, subscription_details_payment_instrument, plan_summary, subscription_details]
- source: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]

### POST(?) /1.0/library/collections/%s/channels/%s

- customer_id:
- marketplace:

### POST(?) /1.0/library/collections/%s/products/%s

- channel_id:

### GET /1.0/catalog/categories

- categories_num_levels: \\d+ (greater than or equal to 1)
- ids: \\d+(,\\d+)\*
- root: [InstitutionsHpMarketing, ChannelsConfigurator, AEReadster, ShortsPrime, ExploreBy, RodizioBuckets, EditorsPicks, ClientContent, RodizioGenres, AmazonEnglishProducts, ShortsSandbox, Genres, Curated, ShortsIntroOutroRemoval, Shorts, RodizioEpisodesAndSeries, ShortsCurated]

### GET /1.0/catalog/categories/%{category_id}

- image_dpi: \\d+
- image_sizes:
- image_variants:
- products_in_plan_timestamp:
- products_not_in_plan_timestamp:
- products_num_results: \\d+
- products_plan: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]
- products_sort_by: [-ReleaseDate, ContentLevel, -Title, AmazonEnglish, AvgRating, BestSellers, -RuntimeLength, ReleaseDate, ProductSiteLaunchDate, -ContentLevel, Title, Relevance, RuntimeLength]
- reviews_num_results: \\d+
- reviews_sort_by: [MostHelpful, MostRecent]

### POST /1.0/content/%{asin}/licenserequest

- B consumption_type: [Streaming, Offline, Download]
- B drm_type: [Hls, PlayReady, Hds, Adrm]
- B quality: [High, Normal, Extreme, Low]
- B num_active_offline_licenses: \\d+ (max: 10)

Example request body:

```json
{
  "drm_type": "Adrm",
  "consumption_type": "Download",
  "quality": "Extreme"
}
```

For a succesful request, returns JSON body with `content_url`.

### GET /1.0/annotations/lastpositions

- asins: asin (comma-separated), e.g. ?asins=B01LWUJKQ7,B01LWUJKQ7,B01LWUJKQ7

### GET /1.0/content/%{asin}/metadata

- response_groups: [chapter_info]
- acr:

### GET /1.0/customer/information

- response_groups: [migration_details, subscription_details_rodizio, subscription_details_premium, customer_segment, subscription_details_channels]

### GET /1.0/customer/status

- response_groups: [benefits_status, member_giving_status, prime_benefits_status, prospect_benefits_status]

### GET /1.0/customer/freetrial/eligibility

### GET /1.0/library/collections

- customer_id:
- marketplace:

### POST(?) /1.0/library/collections

- collection_type:

### GET /1.0/library/collections/%s

- customer_id:
- marketplace:
- page_size:
- continuation_token:

### GET /1.0/library/collections/%s/products

- customer_id:
- marketplace:
- page_size:
- continuation_token:
- image_sizes:

### GET /1.0/stats/aggregates

- daily_listening_interval_duration: ([012]?[0-9])|(30) (0 to 30, inclusive)
- daily_listening_interval_start_date: YYYY-MM-DD (e.g. `2019-06-16`)
- locale: en_US
- monthly_listening_interval_duration: 0?[0-9]|1[012] (0 to 12, inclusive)
- monthly_listening_interval_start_date: YYYY-MM (e.g. `2019-02`)
- response_groups: [total_listening_stats]
- store: [AudibleForInstitutions, Audible, AmazonEnglish, Rodizio]

### GET /1.0/stats/status/finished

- asin: asin

### POST(?) /1.0/stats/status/finished

- start_date:
- status:
- continuation_token:

### GET /1.0/pages/%s

%s: ios-app-home

- locale: en-US
- reviews_num_results:
- reviews_sort_by:
- response_groups: [media, product_plans, view, product_attrs, contributors, product_desc, sample]

### GET /1.0/catalog/products/%{asin}

- image_dpi:
- image_sizes:
- response_groups: [contributors, media, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, review_attrs, reviews, sample, sku]
- reviews_num_results: \\d+ (max: 10)
- reviews_sort_by: [MostHelpful, MostRecent]

### GET /1.0/catalog/products/%{asin}/reviews

- sort_by: [MostHelpful, MostRecent]
- num_results: \\d+ (max: 50)
- page: \\d+

### GET /1.0/catalog/products

- author:
- browse_type:
- category_id: \\d+(,\\d+)\*
- disjunctive_category_ids:
- image_dpi: \\d+
- image_sizes:
- in_plan_timestamp:
- keywords:
- narrator:
- not_in_plan_timestamp:
- num_most_recent:
- num_results: \\d+ (max: 50)
- page: \\d+
- plan: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]
- products_since_timestamp:
- products_sort_by: [-ReleaseDate, ContentLevel, -Title, AmazonEnglish, AvgRating, BestSellers, -RuntimeLength, ReleaseDate, ProductSiteLaunchDate, -ContentLevel, Title, Relevance, RuntimeLength]
- publisher:
- response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_detail, product_plans, rating, review_attrs, reviews, sample, sku]
- reviews_num_results: \\d+ (max: 10)
- reviews_sort_by: [MostHelpful, MostRecent]
- title:

### GET /1.0/recommendations

- category_image_variants:
- image_dpi:
- image_sizes:
- in_plan_timestamp:
- language:
- not_in_plan_timestamp:
- num_results: \\d+ (max: 50)
- plan: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]
- response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, sample, sku]
- reviews_num_results: \\d+ (max: 10)
- reviews_sort_by: [MostHelpful, MostRecent]

### GET /1.0/catalog/products/%{asin}/sims

- category_image_variants:
- image_dpi:
- image_sizes:
- in_plan_timestamp:
- language:
- not_in_plan_timestamp:
- num_results: \\d+ (max: 50)
- plan: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]
- response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plans, rating, review_attrs, reviews, sample, sku]
- reviews_num_results: \\d+ (max: 10)
- reviews_sort_by: [MostHelpful, MostRecent]
- similarity_type: [InTheSameSeries, ByTheSameNarrator, RawSimilarities, ByTheSameAuthor, NextInSameSeries]

## Downloading

For multipart books, it's necessary to use the `child_asin` provided with `response_groups=relationships` in order to download each part.

```python
import audible

client = audible.Client("EMAIL", "PASSWORD", local="us")
license = client.post(
   "content/{asin}/licenserequest",
    body={
        "drm_type": "Adrm",
        "consumption_type": "Download",
        "quality":"Extreme"
    }
)
content_url = license['content_license']['content_metadata']['content_url']['offline_url']

# `content_url` can then be downloaded using any tool

```

Assuming you have your activation bytes, you can convert .aax into another format with the following:

```
$ ffmpeg -activation_bytes 1CEB00DA -i test.aax -vn -c:a copy output.mp4
```
