from application.server import app
app.run(debug=True,  use_reloader=True, host="0.0.0.0", port=5001)
