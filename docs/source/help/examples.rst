========
Examples
========

.. raw:: html

   <div class="skill-level-container">
       <span class="skill-level-badge skill-level-all">All Levels</span>
       <span class="reading-time-badge">10 min read</span>
   </div>

Here are some examples and ideas on how to use this library. Everyone who wants to
provide examples is welcome.

Print number of books for every marketplace::

   import audible

   auth = audible.Authenticator.from_file(filename)
   client = audible.Client(auth)
   country_codes = ["de", "us", "ca", "uk", "au", "fr", "jp", "it", "in"]

   for country in country_codes:
       client.switch_marketplace(country)
       library = client.get("library", num_results=1000)
       asins = [book["asin"] for book in library["items"]]
       print(f"Country: {client.marketplace.upper()} | Number of books: {len(asins)}")
       print(34* "-")

Get listening statistics aggregated month-over-month from 2021-03 to 2021-06::

   import audible

   auth = audible.Authenticator.from_file(filename)
   client = audible.Client(auth)
   with audible.Client(auth=auth) as client:
        stats = client.get(
            "1.0/stats/aggregates",
            monthly_listening_interval_duration="3", #number of months to aggregate for
            monthly_listening_interval_start_date="2021-03", #start month for aggregation
            store="Audible")
