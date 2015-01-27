from flask import Flask, request
from Crypto.PublicKey import RSA
import os
import json
import jws

app = Flask(__name__)

@app.route("/")
def check_status():
    return "Everything is OK"

@app.route("/title", methods=["POST"])
def new_title_version():
    title = json.dumps(request.get_json())

    #import keys
    key_data = open('test_keys/test_private.pem').read()
    key = RSA.importKey(key_data)

    header = { 'alg': 'RS256' }

    sig = jws.sign(header, title, key)

    return str(sig)
