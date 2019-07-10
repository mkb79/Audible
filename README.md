# Audible

[![image](https://img.shields.io/pypi/v/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/l/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/pyversions/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/status/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/wheel/audible.svg)](https://pypi.org/project/audible/)
[![Travis](https://img.shields.io/travis/mkb79/audible/master.svg?logo=travis)](https://travis-ci.org/mkb79/audible)
[![image](https://img.shields.io/pypi/implementation/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/dm/audible.svg)](https://pypi.org/project/audible/)

**Interface for internal Audible API written in pure Python.**

Code including this README is forked from omarroth‘s fantastic [audible.cr](https://github.com/omarroth/audible.cr) API written in crystal.

This package is written with Pythonista for iOS.

This version is still in development and contains many proof of concepts and some need still testing. Feel free to participate.

**The latest stable release is v0.1.5**. 


## Requirements

- Python >= 3.6
- depends on following packages:
	- 	beautifulsoup4
	- 	Pillow
	- 	python-box
	- 	requests
	- 	rsa 

## Installation

```
# v0.1.5
# README for this version here: https://github.com/mkb79/Audible/blob/master/README.md
pip install audible

# v0.2.0-alpha
pip install git+https://github.com/mkb79/audible.git@developing
```

## Usage

**The Usage section is for v0.2.0-alpha only.**

### Basis Examples

```python
import audible

# for US accounts
client = audible.Client.from_login("EMAIL", "PASSWORD", locale="us")

# save session after initializing
client = audible.Client.from_login("EMAIL", "PASSWORD", locale="us", filename="FILENAME")
client.to_json_file()

# restore session from file
# beginning with this version locale code are stored in file
# restoring session from file uses this locale code
# to specify different locales please use ˋlocale="us"ˋ
client = audible.Client.from_json_file(filename="FILENAME")
client =Client.from_json_file(filename="FILENAME", locale="us")

# get library
library = client.get("library", num_results=99, response_groups="media, sample")
print(library)

# specify a api_version on request
# default is api_version="1.0"
# get deprecated version of library
library = client.get("library/books", api_version="0.0", purchaseAfterDate="01/01/1970", sortInAscendingOrder="true")
print(library)

```

### Localizations

At this moment api supports 5 countrys natively.

- USA (locale="us")
- Germany (locale="de")
- United Kingdom (locale="uk")
- France (locale="fr")
- Canada (locale="ca")

You can provide custom locale settings with this code:

```Python
import audible

# example for germany
custom_locale = audible.Locale(
    amazon_login="https://www.amazon.de",
    amazon_api="https://api.amazon.de",
    audible_api="https://api.audible.de",
    accept_language="de-DE",
    marketPlaceId="AN7V1F1VY261K",
    openid_assoc_handle="amzn_audible_ios_de",
    oauth_lang="de-DE",
    auth_register_domain=".amazon.de")

client = audible.Client.from_login(..., locale=custom_locale)

```

You can try to autodetect locale settings like so:

```Python
import audible

# needs the Top Level Domain for the audible page in your country
# example for uk
custom_locale = audible.Locale.from_autodetect_locale("co.uk")

# look if everything is fine
print(custom_locale.to_dict())

# create client
client = audible.Client.from_login(..., locale=custom_locale)

```


### Load and Save sessions

Client session can be saved any time using `to_json_file("FILENAME")` like so:

```python
import audible

client = audible.Client.from_login("EMAIL", "PASSWORD", locale="us")
client.to_json_file("FILENAME")

# Sometime later...
client = audible.Client.from_json_file(filename="FILENAME")

# if restore session with client = audible.Client.from_json_file(filename="FILENAME")
# simply run
client.to_json_file()  # no filename needed
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

client = audible.Client.from_login("EMAIL", "PASSWORD", locale="us", captcha_callback=custom_captcha_callback)
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

client = audible.Client.from_login("EMAIL", "PASSWORD", locale="us", otp_callback=custom_otp_callback)
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

## Authentication

Clients are authenticated using OpenID. Once a client has successfully authenticated with Amazon, they are given an access token and refresh token for authenticating with Audible.

Clients authenticate with Audible using cookies from Amazon and the given access token to `/auth/register`. Clients are given an RSA private key and adp_token used for signing subsequent requests.

For requests to the Audible API, requests need to be signed using the provided key and adp_token. Request signing is fairly straight-forward and uses a signed SHA256 digest. Headers look like:

```
x-adp-alg: SHA256withRSA:1.0
x-adp-signature: AAAAAAAA...:2019-02-16T00:00:01.000000000Z,
x-adp-token: {enc:...}
```

As reference for other implementations, a client **must** store cookies from a successful Amazon login and a working `access_token` in order to renew `refresh_token`, `adp_token`, etc from `/auth/register`.

An `access_token` can be renewed by making a request to `/auth/token`. `access_token`s are valid for 1 hour.
To renew access_token with client call:

```
# refresh access_token if token already expired
# if token valid nothing will be refreshed.
client.refresh_token()

# to force renew of access_token if token is valid
client.refresh_token(force=true)

# if you saved your session before don't forget to save again

```

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

- purchaseAfterDate: mm/dd/yyyy
- sortByColumn: [SHORT_TITLE, strTitle, DOWNLOAD_STATUS, RUNNING_TIME, sortPublishDate, SHORT_AUTHOR, sortPurchDate, DATE_AVAILABLE]
- sortInAscendingOrder: [true, false]

### GET /1.0/library

- num_results: \\d+ (max: 1000)
- page: \\d+
- purchased_after: [RFC3339](https://tools.ietf.org/html/rfc3339) (e.g. `2000-01-01T00:00:00Z`)
- response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, sample, sku, series, reviews, ws4v, origin, relationships, review_attrs, categories, badge_types, category_ladders, claim_code_url, is_downloaded, is_finished, is_returnable, origin_asin, pdf_url, percent_complete, provided_review]
- sort_by: [-Author, -Length, -Narrator, -PurchaseDate, -Title, Author, Length, Narrator, PurchaseDate, Title]

### GET /1.0/library/%{asin}

- response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, sample, sku, series, reviews, ws4v, origin, relationships, review_attrs, categories, badge_types, category_ladders, claim_code_url, is_downloaded, is_finished, is_returnable, origin_asin, pdf_url, percent_complete, provided_review]

### POST(?) /1.0/library/item

- asin:

### POST(?) /1.0/library/item/%s/%s

### GET /1.0/wishlist

- num_results: \\d+ (max: 50)
- page: \\d+
- response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, sample, sku]
- sort_by: [-Author, -DateAdded, -Price, -Rating, -Title, Author, DateAdded, Price, Rating, Title]

### POST /1.0/wishlist

- B asin : String

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

- locale: en_US
- response_groups: brag_message
- store: Audible

### GET /1.0/badges/metadata

- locale: en_US
- response_groups: all_levels_metadata

### GET /1.0/account/information

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
