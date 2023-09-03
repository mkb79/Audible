# Use Postman to request the Audible API

To authenticate to the Audible API, the request have to be signed with the adp_token and the device_private_key obtained after a device registration. [Postman](https://www.postman.com/) don't support this out-of-the-box.

To use Postman for requesting the API, this [pre-request-script](https://github.com/mkb79/Audible/blob/master/utils/postman/pm_pre_request.js) and the [postman-util-lib](https://joolfe.github.io/postman-util-lib/) is needed.

## HOWTO

- Install the postman-util-lib
- Copy the content from the pre-request-script into the `Pre-request Scripts` Tab for the Collection or the single request
- Create an Environment and define the variables `adp-token` and `private-key` with the counterparts from the auth file
