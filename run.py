from application.server import app
# If the reloader is used, then the app is initialised twice.  For normal Flask testing this is fine.  However it
# means that two threads are spawned to republish everything  so its republished twice.
app.run(debug=True,  use_reloader=False, host="0.0.0.0", port=5001)
