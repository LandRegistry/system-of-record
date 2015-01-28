from flask import Flask, request
from Crypto.PublicKey import RSA
import os
import json
import jws

app = Flask(__name__)

@app.route("/")
def check_status():
    return "Everything is OK"

@app.route("/signdata", methods=["POST"])
def new_title_version():
    title = json.dumps(request.get_json())

    #import keys
    key_data = open('test_keys/test_private.pem').read()
    key = RSA.importKey(key_data)

    header = { 'alg': 'RS256' }

    sig = jws.sign(header, title, key)

    return str(sig)


@app.route("/verifydata", methods=["POST"])
def verify_title_version():

    json_as_dict = request.get_json()

    signed_data = json_as_dict['signeddata']

    #signed_data is currently unicode.  Incompatible with JWS.  Convert to ASCII
    signed_data = signed_data.encode('ascii', 'ignore')
    original_data = json.dumps(json_as_dict['originaldata'])

    # #import keys
    key_data = open('test_keys/test_public.pem').read()
    key = RSA.importKey(key_data)

    header = { 'alg': 'RS256' }
    the_result = jws.verify(header, original_data, signed_data, key)

    if the_result:
        return "validated"
    else:
        return "you'll never see this message, jws will show its own."
