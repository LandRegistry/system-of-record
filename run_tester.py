import os

os.environ['SETTINGS'] = "config.DevelopmentConfig"

from Do_not_deploy.query_system_of_record import app
app.run(debug=True, host="0.0.0.0", port=5002)
