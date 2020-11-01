eval( pm.globals.get('pmlib_code') );
var moment = require("moment");

const adpToken = pm.environment.get("adp-token")
const privateKey = pm.environment.get("private-key").replace(/\\n/g, "\n")

signRequest(pm.request, adpToken, privateKey);

function signRequest(request, adpToken, privateKey) {
    const method = request.method;
    const path = request.url.getPathWithQuery();
    const body = request.body || "";
    const date = moment.utc().format();
    const data = `${method}\n${path}\n${date}\n${body}\n${adpToken}`;
    var sig = new pmlib.rs.KJUR.crypto.Signature({"alg": "SHA256withRSA"});
    sig.init(privateKey);
    var hash = sig.signString(data);
    var signedEncoded = pmlib.rs.hex2b64(hash);

    pm.request.headers.add({
        key: 'x-adp-token',
        value: adpToken
    });

    pm.request.headers.add({
        key: 'x-adp-alg',
        value: 'SHA256withRSA:1.0'
    });

    pm.request.headers.add({
        key: 'x-adp-signature',
        value: `${signedEncoded}:${date}`
    });
}
