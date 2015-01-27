from flask import Flask, request
import gnupg
import os
import json

app = Flask(__name__)

@app.route("/")
def check_status():
    return "Everything is OK"

@app.route("/title", methods=["POST"])
def new_title_version():
    title = json.dumps(request.get_json())

    gpg = gnupg.GPG(binary=os.environ.get("gpg_path"))

    #import keys
    key_data = open('test_keys/test_private.key').read()
    private_key = gpg.import_keys(key_data)

    #sign title
    sig = gpg.sign(title, default_key=private_key.fingerprints[0], passphrase="test passphrase")

    print(sig.data)

    return str(sig)
