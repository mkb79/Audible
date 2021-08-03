====================
External Audible API
====================

Documentation
=============

There is currently no publicly available documentation about the 
Audible API.

There is a node client `audible-api <https://github.com/willthefirst/audible/tree/master/node_modules/audible-api>`_ 
that has some endpoints documented, but does not provide information 
on authentication.

Luckily the Audible API is partially self-documenting, however the 
parameter names need to be known. Error responses will look like:

.. code-block:: json

   {
     "message": "1 validation error detected: Value 'some_random_string123' at 'numResults' failed to satisfy constraint: Member must satisfy regular expression pattern: ^\\d+$"
   }

Few endpoints have been fully documented, as a large amount of functionality 
is not testable from the app or functionality is unknown. Most calls need 
to be authenticated.

For `%s` substitutions the value is unknown or can be inferred from the 
endpoint. `/1.0/catalog/products/%s` for example requires an `asin`, 
as in `/1.0/catalog/products/B002V02KPU`.

Each bullet below refers to a parameter for the request with the specified 
method and URL.

Responses will often provide very little info without `response_groups` 
specified. Multiple response groups can be specified, for example: 
`/1.0/catalog/products/B002V02KPU?response_groups=product_plan_details,media,review_attrs`. 
When providing an invalid response group, the server will return an error 
response but will not provide information on available response groups.


.. _api_endpoints:

API Endpoints
=============

.. http:get:: /0.0/library/books
   :deprecated:

   This API endpoint is deprecated. Please use :http:get:`/1.0/library` instead.

   :query string purchaseAfterDate: mm/dd/yyyy
   :query string sortByColumn: [SHORT_TITLE, strTitle, DOWNLOAD_STATUS,
                                RUNNING_TIME, sortPublishDate, SHORT_AUTHOR,
                                sortPurchDate, DATE_AVAILABLE]
   :query bool sortInAscendingOrder: [true, false]

.. http:get:: /1.0/library

   The audible library of current user

   :query integer num_results: (max: 1000)
   :query integer page: page
   :query string purchased_after: [RFC3339](https://tools.ietf.org/html/rfc3339)
                                  (e.g. `2000-01-01T00:00:00Z`)
   :query string title: a title
   :query string author: a author
   :query string response_groups: [contributors, customer_rights, media, price,
                                   product_attrs, product_desc,
                                   product_extended_attrs, product_plan_details,
                                   product_plans, rating, sample, sku, series,
                                   reviews, ws4v, origin, relationships,
                                   review_attrs, categories, badge_types,
                                   category_ladders, claim_code_url, is_downloaded,
                                   is_finished, is_playable, is_removable,
                                   is_returnable, is_visible, order_details,
                                   origin_asin, pdf_url, percent_complete,
                                   provided_review]
   :query string image_sizes: [1215,408,360,882,315,570,252,558,900,500]
   :query string sort_by: [-Author, -Length, -Narrator, -PurchaseDate, -Title,
                           Author, Length, Narrator, PurchaseDate, Title]
   :query string status: [Active, Revoked] ('Active' is the default, 'Revoked'
                         returns audiobooks the user has returned for a refund.)
   :query string parent_asin: asin

.. http:get:: /1.0/library/(string:asin)

   :param asin: The asin of the book
   :type asin: string
   :query string response_groups: [contributors, media, price, product_attrs,
                                   product_desc, product_extended_attrs,
                                   product_plan_details, product_plans, rating,
                                   sample, sku, series, reviews, ws4v, origin,
                                   relationships, review_attrs, categories,
                                   badge_types, category_ladders, claim_code_url,
                                   is_downloaded, is_finished, is_returnable,
                                   origin_asin, pdf_url, percent_complete,
                                   provided_review]

.. http:post:: /1.0/library/item

   :<json string asin: The asin of the book

POST(?) /1.0/library/item
-------------------------

:body:
   - asin

POST(?) /1.0/library/item/%s/%s
-------------------------------

:body:
   -

POST(?) /1.0/library/collections/%s/channels/%s
-----------------------------------------------

:body:
   - customer_id:
   - marketplace:

POST(?) /1.0/library/collections/%s/products/%s
-----------------------------------------------

:body:
   - channel_id:

GET /1.0/library/collections
----------------------------

:params:
   - customer_id:
   - marketplace:

POST(?) /1.0/library/collections
--------------------------------

:body:
   - collection_type:

GET /1.0/library/collections/%s
-------------------------------

:params:
   - customer_id:
   - marketplace:
   - page_size:
   - continuation_token:

GET /1.0/library/collections/%s/products
----------------------------------------

:params:
   - customer_id:
   - marketplace:
   - page_size:
   - continuation_token:
   - image_sizes:

GET /1.0/collections
--------------------

:params:

POST /1.0/collections
---------------------

Create a new collection

:body:
   - name: 
   - asins: []
   - description

:returns:
   - collection_id
   - creation_date
   - customer_id
   - marketplace

GET /1.0/collections/%{collection_id}
-------------------------------------

:params:

PUT /1.0/collections/%{collection_id}
-------------------------------------

Modify a collection

:body:
   - state_token
   - collection_id: %{collection_id}
   - name
   - description

:returns:
   - state_token
   - collection_id: %{collection_id}
   - name
   - description

GET /1.0/collections/%{collection_id}/items
-------------------------------------------

:params:
   - response_groups: [always-returned]

POST /1.0/collections/%{collection_id}/items
--------------------------------------------

Add item(s) to a collection

:body:
   - collection_id: %{collection_id}
   - asins: []

:returns:
   - description
   - name
   - num_items_added: int
   - state_token

GET /1.0/orders
---------------

 :params:
    - unknown

 Returns order history from at least the past 6 months. Supports pagination.

POST /1.0/orders
----------------

:body:
   - asin: String
   - audiblecreditapplied: String

Example request body:

.. code-block:: json

   {
     "asin": "B002V1CB2Q",
     "audiblecreditapplied": "false"
   }

- audiblecreditapplied: [true, false]

`audiblecreditapplied` will specify whether to use available credits 
or default payment method.

GET /1.0/wishlist
-----------------

:params:
   - num_results: \\d+ (max: 50)
   - page: \\d+
   - response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, sample, sku, customer_rights, relationships]
   - sort_by: [-Author, -DateAdded, -Price, -Rating, -Title, Author, DateAdded, Price, Rating, Title]

POST /1.0/wishlist
------------------

:body:
   - asin: String

Example request body:

.. code-block:: json

   {
     "asin": "B002V02KPU"
   }

Returns 201 and a `Location` to the resource.

DELETE /1.0/wishlist/%{asin}
----------------------------

Returns 204 and removes the item from the wishlist using the given `asin`.

GET /1.0/badges/progress
------------------------

:params:
   - locale: en_US
   - response_groups: brag_message
   - store: [AudibleForInstitutions, Audible, AmazonEnglish, Rodizio]

GET /1.0/badges/metadata
------------------------

:params:
   - locale: en_US
   - response_groups: all_levels_metadata

GET /1.0/account/information
----------------------------

:params:
   - response_groups: [delinquency_status, customer_benefits, subscription_details_payment_instrument, plan_summary, subscription_details]
   - source: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]

GET /1.0/catalog/categories
---------------------------

:params:
   - response_groups: [category_metadata, products]
   - products_plan = [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, US Minerva, Universal, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]
   - products_in_plan_timestamp:
   - products_num_results:
   - runtime_length_min:
   - content_level:
   - content_type:
   - categories_num_levels: \\d+ (greater than or equal to 1)
   - ids: \\d+(,\\d+)\*
   - root: [InstitutionsHpMarketing, ChannelsConfigurator, AEReadster, ShortsPrime, ExploreBy, RodizioBuckets, EditorsPicks, ClientContent, RodizioGenres, AmazonEnglishProducts, ShortsSandbox, Genres, Curated, ShortsIntroOutroRemoval, Shorts, RodizioEpisodesAndSeries, ShortsCurated]

GET /1.0/catalog/categories/%{category_id}
------------------------------------------

:params:
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

GET /1.0/catalog/products/%{asin}
---------------------------------

:params:
   - image_dpi:
   - image_sizes:
   - response_groups: [contributors, media, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, review_attrs, reviews, sample, sku]
   - reviews_num_results: \\d+ (max: 10)
   - reviews_sort_by: [MostHelpful, MostRecent]
   - asins

GET /1.0/catalog/products/%{asin}/reviews
-----------------------------------------

:params:
   - sort_by: [MostHelpful, MostRecent]
   - num_results: \\d+ (max: 50)
   - page: \\d+

GET /1.0/catalog/products
-------------------------

:params:
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

GET /1.0/catalog/products/%{asin}/sims
--------------------------------------

:params:
   - category_image_variants:
   - image_dpi::param:- image_sizes:
   - in_plan_timestamp:
   - language:
   - not_in_plan_timestamp:
   - num_results: \\d+ (max: 50)
   - plan: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]
   - response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plans, rating, review_attrs, reviews, sample, sku]
   - reviews_num_results: \\d+ (max: 10)
   - reviews_sort_by: [MostHelpful, MostRecent]
   - similarity_type: [InTheSameSeries, ByTheSameNarrator, RawSimilarities, ByTheSameAuthor, NextInSameSeries]

.. http:post:: /1.0/content/(string:asin)/licenserequest

   :param asin: The asin of the book
   :type asin: string
   :<json string supported_drm_types: [Mpeg, Adrm]
   :<json string consumption_type: [Streaming, Offline, Download]
   :<json string drm_type: [Hls, PlayReady, Hds, Adrm]
   :<json string quality: [High, Normal, Extreme, Low]
   :<json integer num_active_offline_licenses: (max: 10)
   :<json string response_groups: [last_position_heard, pdf_url,
                                   content_reference, chapter_info]

POST /1.0/content/%{asin}/licenserequest
----------------------------------------

:body:
   - supported_drm_types: [Mpeg, Adrm]
   - consumption_type: [Streaming, Offline, Download]
   - drm_type: [Mpeg, PlayReady, Hls, Dash, FairPlay, Widevine, HlsCmaf, Adrm]
   - quality: [High, Normal, Extreme, Low]
   - num_active_offline_licenses: \\d+ (max: 10)
   - response_groups: [last_position_heard,pdf_url,content_reference,chapter_info]

Example request body:

.. code-block:: json

    {
        "supported_drm_types" : [
            "Mpeg",
            "Adrm"
        ],
        "quality" : "High",
        "consumption_type" : "Download",
        "response_groups" : "last_position_heard,pdf_url,content_reference,chapter_info"
    }

For a succesful request, returns JSON body with `content_url`.

GET /1.0/content/%{asin}/metadata
---------------------------------

:params:
   - response_groups: [chapter_info, always-returned, content_reference, content_url]
   - acr:
   - quality: [High, Normal, Extreme, Low]
   - drm_type: [Hls, Dash, HlsCmaf, Adrm]
   

GET /1.0/annotations/lastpositions
----------------------------------

:params:
   - asins: asin (comma-separated), e.g. ?asins=B01LWUJKQ7,B01LWUJKQ7,B01LWUJKQ7

GET /1.0/customer/information
-----------------------------

:params:
   - response_groups: [migration_details, subscription_details_rodizio, subscription_details_premium, customer_segment, subscription_details_channels]

GET /1.0/customer/status
------------------------

:params:
   - response_groups: [benefits_status, member_giving_status, prime_benefits_status, prospect_benefits_status]

GET /1.0/customer/freetrial/eligibility
---------------------------------------

:params:
   -

GET /1.0/stats/aggregates
-------------------------

:params:
   - daily_listening_interval_duration: ([012]?[0-9])|(30) (0 to 30, inclusive)
   - daily_listening_interval_start_date: YYYY-MM-DD (e.g. `2019-06-16`)
   - locale: en_US
   - monthly_listening_interval_duration: 0?[0-9]|1[012] (0 to 12, inclusive)
   - monthly_listening_interval_start_date: YYYY-MM (e.g. `2019-02`)
   - response_groups: [total_listening_stats]
   - store: [AudibleForInstitutions, Audible, AmazonEnglish, Rodizio]

GET /1.0/stats/status/finished
------------------------------

:params:
   - asin: asin
   - start_date: [RFC3339](https://tools.ietf.org/html/rfc3339) (e.g. `2000-01-01T00:00:00Z`)

POST(?) /1.0/stats/status/finished
----------------------------------

:body:
   - start_date:
   - status:
   - continuation_token:

PUT /1.0/stats/events
---------------------

:body:
   - stats

Example request body:

.. code-block:: json

    {
        "stats" : [
            {
                "download_start" : {
                    "country_code" : "de",
                    "download_host" : "xxxxx.cloudfront.net",
                    "user_agent" : "Audible, iPhone, 3.35.1 (644), iPhone XS (iPhone11,2), 238 GB, iOS, 14.1, Wifi",
                    "request_id" : "xxxxxxxxxxxx",
                    "codec" : "AAX_44_128",
                    "source" : "audible_iPhone"
                },
                "social_network_site" : "Unknown",
                "event_type" : "DownloadStart",
                "listening_mode" : "Offline",
                "local_timezone" : "Europe\/Berlin",
                "asin_owned" : false,
                "playing_immersion_reading" : false,
                "audio_type" : "FullTitle",
                "event_timestamp" : "2020-10-23T21:29:06.985Z",
                "asin" : "xxxxxxx",
                "store" : "Audible",
                "delivery_type" : "Download"
            }
        ]
    }

GET /1.0/pages/%s
-----------------

%s: ios-app-home

:params:
   - locale: en-US
   - reviews_num_results:
   - reviews_sort_by:
   - response_groups: [media, product_plans, view, product_attrs, contributors, product_desc, sample]

GET /1.0/recommendations
------------------------

:params:
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

GET /1.0/user/settings
----------------------

:params:
   - setting_name: [captionsEnabled]
