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

Library
-------

.. http:get:: /1.0/library

   The audible library of current user

   :query integer num_results: (max: 1000)
   :query integer page: page
   :query string purchased_after: [RFC3339](https://tools.ietf.org/html/rfc3339)
                                  (e.g. `2000-01-01T00:00:00Z`)
   :query string title: a title
   :query string author: a author
   :query string response_groups: [contributors, customer_rights, media, price,
                                   product_attrs, product_desc, product_details,
                                   product_extended_attrs, product_plan_details,
                                   product_plans, rating, sample, sku, series,
                                   reviews, ws4v, origin, relationships,
                                   review_attrs, categories, badge_types,
                                   category_ladders, claim_code_url, in_wishlist, is_archived, is_downloaded,
                                   is_finished, is_playable, is_removable,
                                   is_returnable, is_visible, listening_status, order_details,
                                   origin_asin, pdf_url, percent_complete, periodicals,
                                   provided_review]
   :query string image_sizes: [1215,408,360,882,315,570,252,558,900,500]
   :query string sort_by: [-Author, -Length, -Narrator, -PurchaseDate, -Title,
                           Author, Length, Narrator, PurchaseDate, Title]
   :query string status: [Active, Revoked] ('Active' is the default, 'Revoked'
                         returns audiobooks the user has returned for a refund.)
   :query string parent_asin: asin
   :query string include_pending: [true, false]
   :query string marketplace: [e.g. AN7V1F1VY261K]
   :query string state_token:

.. http:get:: /1.0/library/(string:asin)

   :param asin: The asin of the book
   :type asin: string
   :query string response_groups: [contributors, media, price, product_attrs,
                                   product_desc, product_details, product_extended_attrs,
                                   product_plan_details, product_plans, rating,
                                   sample, sku, series, reviews, ws4v, origin,
                                   relationships, review_attrs, categories,
                                   badge_types, category_ladders, claim_code_url,
                                   is_downloaded, is_finished, is_returnable,
                                   origin_asin, pdf_url, percent_complete,
                                   periodicals, provided_review]

.. http:post:: /1.0/library/item

   :<json string asin: The asin of the book

.. http:post:: /1.0/library/item

   :<json asin:

.. http:put:: /1.0/library/item

   Add an (AYCL) item to the library

   :<json asin:

.. http:post:: /1.0/library/item/(param1)/(param2)

   :param param1:
   :param param2:

   :<json unknown:

.. http:post:: /1.0/library/collections/(param1)/channels/(param2)

   :param param1:
   :param param2:

   :<json customer_id:
   :<json marketplace:

.. http:post:: /1.0/library/collections/(param1)/products/(param2)

   :param param1:
   :param param2:

   :<json channel_id:

.. http:get:: /1.0/library/collections

   :query customer_id:
   :query marketplace:

.. http:post:: /1.0/library/collections

   :<json collection_type:

.. http:get:: /1.0/library/collections/(param1)

   :param param1:
   :query customer_id:
   :query marketplace:
   :query page_size:
   :query continuation_token:

.. http:get:: /1.0/library/collections/(param1)/products

   :param param1:
   :query customer_id:
   :query marketplace:
   :query page_size:
   :query continuation_token:
   :query image_sizes:

Catalog
-------

Categories
^^^^^^^^^^

.. http:get:: /1.0/catalog/categories

   :query response_groups: [category_metadata, products]
   :query products_plan: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, US Minerva, Universal, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]
   :query products_in_plan_timestamp:
   :query products_num_results:
   :query runtime_length_min:
   :query content_level:
   :query content_type:
   :query int categories_num_levels: (greater than or equal to 1)
   :query ids: \\d+(,\\d+)\*
   :query root: [InstitutionsHpMarketing, ChannelsConfigurator, AEReadster, ShortsPrime, ExploreBy, RodizioBuckets, EditorsPicks, ClientContent, RodizioGenres, AmazonEnglishProducts, ShortsSandbox, Genres, Curated, ShortsIntroOutroRemoval, Shorts, RodizioEpisodesAndSeries, ShortsCurated]

.. http:get:: /1.0/catalog/categories/(category_id)

   :param category_id:
   :query int image_dpi:
   :query image_sizes:
   :query image_variants:
   :query products_in_plan_timestamp:
   :quers products_not_in_plan_timestamp:
   :query int products_num_results:
   :query products_plan: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]
   :query products_sort_by: [-ReleaseDate, ContentLevel, -Title, AmazonEnglish, AvgRating, BestSellers, -RuntimeLength, ReleaseDate, ProductSiteLaunchDate, -ContentLevel, Title, Relevance, RuntimeLength]
   :query int reviews_num_results:
   :query reviews_sort_by: [MostHelpful, MostRecent]

Products
^^^^^^^^

.. http:get:: /1.0/catalog/products/(string:asin)

   :param asin: The asin of the book
   :type asin: string
   :query image_dpi:
   :query image_sizes:
   :query response_groups: [contributors, media, price, product_attrs, product_desc, product_details, product_extended_attrs, product_plan_details, product_plans, rating, sample, sku, series, reviews, relationships, review_attrs, category_ladders, claim_code_url, provided_review, rights, customer_rights, goodreads_ratings]
   :query reviews_num_results: \\d+ (max: 10)
   :query reviews_sort_by: [MostHelpful, MostRecent]
   :query asins:

.. http:get:: /1.0/catalog/products

   :query asins:
   :query image_sizes: [1215,408,360,882,315,570,252,558,900]
   :query response_groups: [sku,product_attrs,rating,product_extended_attrs,media,sample,product_plans,product_plan_details,badges,relationships,customer_rights,product_desc,contributors]

.. http:get:: /1.0/catalog/products/(string:asin)/reviews

   :param asin: The asin of the book
   :type asin: string
   :query sort_by: [MostHelpful, MostRecent]
   :query int num_results: (max: 50)
   :query int page:

.. http:get:: /1.0/catalog/products

   :query author:
   :query browse_type:
   :query int category_id: \\d+(,\\d+)\*
   :query disjunctive_category_ids:
   :query int image_dpi:
   :query image_sizes:
   :query in_plan_timestamp:
   :query keywords:
   :query narrator:
   :query not_in_plan_timestamp:
   :query num_most_recent:
   :query int num_results: (max: 50)
   :query int page:
   :query plan: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]
   :query products_since_timestamp:
   :query products_sort_by: [-ReleaseDate, ContentLevel, -Title, AmazonEnglish, AvgRating, BestSellers, -RuntimeLength, ReleaseDate, ProductSiteLaunchDate, -ContentLevel, Title, Relevance, RuntimeLength]
   :query publisher:
   :query response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, review_attrs, reviews, sample, series, sku]
   :query int reviews_num_results: (max: 10)
   :query reviews_sort_by: [MostHelpful, MostRecent]
   :query title:

.. http:get:: /1.0/catalog/products/(string:asin)/sims

   :param asin: The asin of the book
   :type asin: string
   :query category_image_variants:
   :query image_dpi:
   :query image_sizes:
   :query in_plan_timestamp:
   :query language:
   :query not_in_plan_timestamp:
   :query int num_results: (max: 50)
   :query plan: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]
   :query response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plans, rating, review_attrs, reviews, sample, sku]
   :query int reviews_num_results: (max: 10)
   :query reviews_sort_by: [MostHelpful, MostRecent]
   :query similarity_type: [InTheSameSeries, ByTheSameNarrator, RawSimilarities, ByTheSameAuthor, NextInSameSeries]

Collections
-----------

.. http:get:: /1.0/collections

   :query state_token: [ey...]
   :query visibility_types: [Private, Discoverable]

.. http:post:: /1.0/collections

   Create a new collection

   :<json name:
   :<json asins: []
   :<json description:

   :>json collection_id:
   :>json creation_date:
   :>json customer_id:
   :>json marketplace:

.. http:get:: /1.0/collections/(collection_id)

   :param collection_id:

.. http:put:: /1.0/collections/(collection_id)

   Modify a collection

   :param collection_id:

   :<json state_token:
   :<json collection_id:
   :<json name:
   :<json description:

   :>json state_token:
   :>json collection_id:
   :>json name:
   :>json description:

.. http:get:: /1.0/collections/(collection_id)/items

   :param collection_id: e.g __FAVORITES
   :query response_groups: [always-returned]

.. http:post:: /1.0/collections/(collection_id)/items

   Add item(s) to a collection

   :param collection_id:
   :<json collection_id:
   :<json asins: []

   :>json description:
   :>json name:
   :>json int num_items_added:
   :>json state_token:

Orders
------

.. http:get:: /1.0/orders

   Returns order history from at least the past 6 months. Supports pagination.

   :query unknown:

.. http:post:: /1.0/orders

   :<json string asin:
   :<json boolean audiblecreditapplied: will specify whether to use available credits or default payment method.

   **Example request body**

   .. code-block:: json

      {
        "asin": "B002V1CB2Q",
        "audiblecreditapplied": "false"
      }

Wishlist
--------

.. http:get:: /1.0/wishlist

   :query int num_results: (max: 50)
   :query int page: (wishlist start at page 0)
   :query string locale: e.g. de-DE
   :query response_groups: [contributors, media, price, product_attrs, product_desc, product_extended_attrs, product_plan_details, product_plans, rating, sample, sku, customer_rights, relationships]
   :query sort_by: [-Author, -DateAdded, -Price, -Rating, -Title, Author, DateAdded, Price, Rating, Title]

.. http:post:: /1.0/wishlist

   :<json string asin: The asin of the book to add
   :statuscode 201: Returns the `Location` to the resource.

   **Example request body**

   .. code-block:: json

      {
        "asin": "B002V02KPU"
      }

.. http:delete:: /1.0/wishlist/(string:asin)

   :param asin: The asin of the book
   :type asin: string
   :statuscode 204: Removes the item from the wishlist using the given `asin`.

.. http:get:: /1.0/badges/progress

   :query locale: en_US
   :query response_groups: brag_message
   :query store: [AudibleForInstitutions, Audible, AmazonEnglish, Rodizio]

Badges
------

.. http:get:: /1.0/badges/metadata

   :query locale: en_US
   :query response_groups: all_levels_metadata

Content
-------

.. http:post:: /1.0/content/(string:asin)/licenserequest

   :param asin: The asin of the book
   :type asin: string
   :<json boolean use_adaptive_bit_rate: [true, false]
   :<json string quality: [High, Normal]
   :<json string chapter_titles_type: [Tree, Flat]
   :<json string response_groups: [chapter_info, content_reference,
                                   last_position_heard, pdf_url,
                                   ad_insertion, certificate]
   :<json string consumption_type: [Streaming, Offline, Download]
   :<json boolean spatial: [true, false]
   :<json dict supported_media_features: [codecs, drm_types]
   :<json list codecs: [mp4a.40.2, mp4a.40.42, ec+3, ac-4]
   :<json list drm_types: [Mpeg, PlayReady, Hls, Dash, Adrm,
                             FairPlay, Widevine, HlsCmaf]
   :<json integer num_active_offline_licenses: (max: 10)

   **Example request body**

   .. code-block:: json

       {
           "quality": "High",
           "response_groups": "chapter_info,content_reference,last_position_heard,pdf_url, ad_insertion, certificate",
           "consumption_type": "Download",
           "supported_media_features":
               {
                   "codecs": [
                       "mp4a.40.2",
                       "mp4a.40.42",
                       "ec+3",
                       "ac-4"
                   ],
                   "drm_types": [
                       "Mpeg",
                       "PlayReady",
                       "Hls",
                       "Dash",
                       "Adrm",
                       "FairPlay",
                       "Widevine",
                       "HlsCmaf",
                   ]
               },
           "spatial": false
       }

   For a succesful request, returns JSON body with `content_url`.

.. http:post:: /1.0/content/(string:asin)/licenserequest
   :noindex:

   **licenserequest (current app variant)** — same endpoint as above, documented
   separately to capture the full set of fields sent by the current Audible
   Android app. ``supported_media_features`` carries the codec/DRM selection.

   :param asin: The asin of the book
   :type asin: string
   :<json string response_groups: [chapter_info, content_reference, last_position_heard,
                                   pdf_url, ad_insertion, certificate, content_url,
                                   relationships, ebook_companion]
   :<json string acr: Audible Content Reference (to re-license a known version)
   :<json string version: content version
   :<json string file_version: content file version
   :<json dict supported_media_features: codec/DRM selection, see fields below
   :<json list drm_types: within supported_media_features — [Adrm, Mpeg, Dash, Hls,
                          PlayReady, Widevine]
   :<json list codecs: within supported_media_features — [mp4a.40.2, mp4a.40.42, ec+3,
                       ac-4, avc1]
   :<json string chapter_titles_type: within supported_media_features — [Tree, Flat]
   :<json boolean previews: within supported_media_features
   :<json boolean catalog_samples: within supported_media_features
   :<json list visual_drm_types: within supported_media_features
   :<json boolean spatial: [true, false]
   :<json string consumption_type: [Streaming, Offline, Download]
   :<json string quality: [Low, Normal, High, Extreme]
   :<json boolean use_adaptive_bit_rate: [true, false]
   :<json string tenant_id: Audible
   :<json string rights_validation:
   :<json list supported_rights_types: [Ownership, Membership, AYCL, Radio,
                                        EbookOwnership, Client]
   :<json list supported_features:
   :<json integer playback_start_ms:
   :<json integer playback_end_ms:
   :<json dict ebook_companion:

   **Example request body**

   .. code-block:: json

       {
           "consumption_type": "Download",
           "response_groups": "last_position_heard,pdf_url,content_reference,chapter_info",
           "quality": "High",
           "tenant_id": "Audible",
           "spatial": false,
           "supported_media_features": {
               "drm_types": ["Mpeg", "Adrm"],
               "codecs": ["mp4a.40.2", "mp4a.40.42"],
               "chapter_titles_type": "Tree"
           }
       }

   :>json object content_license: contains ``acr``, ``content_metadata``
      (``content_reference``, ``chapter_info``, ``content_url``), ``drm_type``,
      ``license_response`` (the encrypted voucher / DRM license), ``license_id``,
      ``allowed_users``, ``status_code``, ``refresh_date``, ``removal_date``,
      ``granted_right``, ``pdf_url``

.. http:get:: /1.0/content/(string:asin)/metadata

   :param asin: the asin of the book
   :type asin: string
   :query response_groups: [chapter_info, always-returned, content_reference, content_url]
   :query acr:
   :query quality: [High, Normal]
   :query chapter_titles_type: [Tree, Flat]
   :query drm_type: [Mpeg, PlayReady, Hls, Dash, FairPlay, Widevine, HlsCmaf, Adrm]

.. http:post:: /1.0/content/(string:asin)/drmlicense

   :param asin: The asin of the book
   :type asin: string
   :<json string licenseChallenge: The license challenge
   :<json string asin: The asin of the book
   :<json string consumption_type: "Download"
   :<json string drm_type: "FairPlay"
   :>json string license: The encrypted license

.. http:get:: 1.0/content/FairPlay/certificate

   :>json string certificate: The base64 encoded FairPlay certificate

.. http:post:: /1.0/content-license-refresh

   Refreshes (renews) the DRM licenses/vouchers for one or more titles in a
   single batch request. Used to keep offline downloads playable before their
   ``license_removal_date`` / ``license_expiration_date`` is reached, without
   requesting a full ``licenserequest`` per title.

   :<json array license_refresh_requests: list of refresh request objects (see below)
   :<json string tenant_id: Audible
   :<json array supported_rights_types: optional, e.g. [Ownership, Membership]

   Each object in ``license_refresh_requests``:

   :<json string asin: the title ASIN
   :<json string acr: Audible Content Reference, from a prior licenserequest
   :<json string file_version: content file version, from a prior licenserequest
   :<json string drm_type: [Adrm, Widevine, Dash, Hls, PlayReady, Mpeg]
   :<json string drm_challenge: base64 CDM challenge; only required for Widevine
                                (null for Adrm)

   :>json string request_id: request identifier (may be null)
   :>json array license_refresh_responses: list of per-title results (see below)

   Each object in ``license_refresh_responses``:

   :>json string asin: the title ASIN
   :>json array allowed_users: directed IDs allowed to use the license
   :>json string access_expiry_date: access expiry timestamp
   :>json string granted_right: e.g. Ownership, Membership, AYCL
   :>json string license: refreshed license/voucher (for Adrm the encrypted voucher)
   :>json object license_metadata: ``license_id``, ``license_refresh_date``,
      ``license_removal_date``, ``license_expiration_date``
   :>json object status: ``status_code``, ``license_denial_reasons``, ``error_message``

   :statuscode 200: batch processed; individual titles may still be denied via
                    ``status.status_code``

   **Example request body**

   .. code-block:: json

       {
           "license_refresh_requests": [
               {
                   "asin": "B0XXXXXXXX",
                   "acr": "CR!...",
                   "file_version": "1",
                   "drm_type": "Adrm"
               }
           ],
           "tenant_id": "Audible"
       }

.. http:post:: /1.0/content/(string:asin)/playback-state

   Returns playback state for a title, primarily the last position heard (LPH)
   together with content/product metadata.

   :param asin: The asin of the book
   :type asin: string
   :<json string asin: the title ASIN
   :<json string acr: Audible Content Reference
   :<json string tenant_id: Audible
   :<json dict supported_media_features: codec/DRM selection
   :<json string chapter_titles_type: [Tree, Flat]
   :<json list supported_features: optional feature flags
   :<json string response_groups: [last_position_heard, content_reference, chapter_info]

   :>json object last_position_heard: last listening position (status + position in ms)
   :>json array response_groups: echoes the groups returned
   :>json object content_metadata: ``content_reference``, ``chapter_info``,
      ``content_url``, ``last_position_heard``
   :>json object product_metadata: product-level metadata
   :>json string timeline_sidecar_url: URL of the timeline sidecar, if present

.. http:get:: /1.0/content/(string:asin)/supplementalassetmetadata/

   Returns metadata for the supplemental assets of a title, e.g. an eBook
   companion (Immersion Reading / Whispersync) or its sync file.

   :param asin: The asin of the book
   :type asin: string
   :query acr: Audible Content Reference of the title
   :query response_groups: [ebook_companion, ebook_sync_file]
   :query ebook_asin: ASIN of the companion eBook (required for ebook_sync_file)
   :query ebook_acr: ACR of the companion eBook (used with ebook_sync_file)
   :query tenant_id: Audible

   :>json array response_groups: echoes the groups returned, e.g.
      [always-returned, ebook_companion]
   :>json object ebook_companion_metadata: ``asin``, ``acr``, ``version``
      (empty object if the title has no companion)
   :>json array supplemental_assets: list of supplemental asset objects (empty if none)

   :statuscode 200: metadata returned
   :statuscode 400: invalid response group, or the ASIN is a non-audio asset
                    (e.g. PodcastParent)

.. http:get:: /1.0/content/(string:asin)/recap

   Returns a generated "Recap" (a short catch-up summary of what has been heard
   so far, from the last position) as an audio asset.

   :param asin: The asin of the book
   :type asin: string
   :query acr: Audible Content Reference
   :query recap_mode: recap mode selector
   :query voice: narration voice
   :query language: recap language
   :query lph_ms: last position heard, in milliseconds
   :query lph_timestamp: timestamp of the last position heard
   :query supported_codecs: repeatable; supported audio codecs
   :query supported_drm_types: repeatable; supported DRM types

   :>json object recap_metadata: ``asin``, ``acr``, ``status``, ``drm_type``,
      ``denial_reason``, ``license_id``, ``recap_url``

Account
-------

.. http:get:: /1.0/account/information

   :query response_groups: [delinquency_status, customer_benefits, customer_segments, subscription_details_payment_instrument, plan_summary, subscription_details, directed_ids]
   :query source: [Credit, Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat, AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio, SpecialBenefit, Rodizio]


Customer
--------

.. http:get:: /1.0/customer/information

   :query response_groups: [migration_details, subscription_details_rodizio, subscription_details_premium, customer_segment, subscription_details_channels]

.. http:get:: /1.0/customer/status

   :query response_groups: [benefits_status, member_giving_status, prime_benefits_status, prospect_benefits_status]

.. http:get:: /1.0/customer/freetrial/eligibility

Stats
-----

.. http:get:: /1.0/stats/aggregates

   :query daily_listening_interval_duration: ([012]?[0-9])|(30) (0 to 30, inclusive)
   :query daily_listening_interval_start_date: YYYY-MM-DD (e.g. `2019-06-16`)
   :query locale: en_US
   :query monthly_listening_interval_duration: 0?[0-9]|1[012] (0 to 12, inclusive)
   :query monthly_listening_interval_start_date: YYYY-MM (e.g. `2019-02`)
   :query response_groups: [total_listening_stats]
   :query store: [AudibleForInstitutions, Audible, AmazonEnglish, Rodizio]

.. http:get:: /1.0/stats/status/finished

   :query asin: asin
   :query start_date: [RFC3339](https://tools.ietf.org/html/rfc3339) (e.g. `2000-01-01T00:00:00Z`)


.. http:post:: /1.0/stats/status/finished

   :<json start_date:
   :<json status:
   :<json continuation_token:

.. http:put:: /1.0/stats/events

   :<json stats:

   **Example request body**

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

Misc
-----

.. http:get:: /1.0/actors

   :query bool include_enrolled: [true, false]
   :query bool include_suggested: [true, false]

.. http:get:: /1.0/annotations/lastpositions

   :query asins: asin (comma-separated), e.g. ?asins=B01LWUJKQ7,B01LWUJKQ7,B01LWUJKQ7

.. http:put:: /1.0/lastpositions/(string:asin)

   :param asin: the asin of the book
   :type asin: string
   :<json acr: obtained by :http:post:`/1.0/content/(string:asin)/licenserequest`
   :<json asin:
   :<json position_ms:

.. http:get:: /1.0/pages/(string:param1)

   :param param1: [ios-app-home]
   :type param1: string
   :query int image_dpi: [489]
   :query local_time: [2022-01-01T12:00:00+01:00]
   :query locale: en-US
   :query os: [15.2]
   :query reviews_num_results:
   :query reviews_sort_by:
   :query response_groups: [media, product_plans, view, product_attrs,
                            contributors, product_desc, sample]
   :query session_id: [123-1234567-1234567]
   :query surface: [iOS]

.. http:get:: /1.0/recommendations

   :query category_image_variants:
   :query category_image_variants:
   :query image_dpi:
   :query image_sizes:
   :query in_plan_timestamp:
   :query language:
   :query not_in_plan_timestamp:
   :query int num_results: (max: 50)
   :query plan: [Enterprise, RodizioFreeBasic, AyceRomance, AllYouCanEat,
                 AmazonEnglish, ComplimentaryOriginalMemberBenefit, Radio,
                 SpecialBenefit, Rodizio]
   :query response_groups: [contributors, media, price, product_attrs,
                            product_desc, product_extended_attrs,
                            product_plan_details, product_plans, rating, sample, sku]
   :query int reviews_num_results: (max: 10)
   :query reviews_sort_by: [MostHelpful, MostRecent]

.. http:get:: /1.0/user/settings

   :query string setting_name: [captionsEnabled]

.. http:get:: /1.0/app/upgradestatus

   :query version: [3.68]
   :query app_id: [A2CZJZGLK2JJVM]
   :query operating_system: [iOS15.4]

.. http:get:: https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/sidecar

   Returns the clips, notes and bookmarks of a book

   :query string type: ["AUDI"]
   :query string key: asin of the book
