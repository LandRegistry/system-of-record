#!/bin/bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir

virtualenv -p python3 ~/venvs/system-of-record
source ~/venvs/system-of-record/bin/activate
pip install -r requirements.txt

#Set environment variable in supervisord according to deploying environment (default to development)
case "$DEPLOY_ENVIRONMENT" in
  development)
  SETTINGS="config.DevelopmentConfig"
  ;;
  test)
  SETTINGS="config.TestConfig"
  ;;
  preproduction)
  SETTINGS="config.PreproductionConfig"
  ;;
  production)
  SETTINGS="config.ProductionConfig"
  ;;
  *)
  SETTINGS="config.DevelopmentConfig"
  ;;
esac

#Set this environment variable for python db migrations
export SETTINGS=$SETTINGS

python manage.py db upgrade

echo "Adding system of record to supervisord..."
cat > /etc/supervisord.d/systemofrecord.ini << EOF
[program:systemofrecord]
command=$HOME/venvs/system-of-record/bin/gunicorn --log-file=- --log-level DEBUG -b 0.0.0.0:5000 --timeout 120 application.server:app
directory=$dir
autostart=true
autorestart=true
user=$USER
environment=SETTINGS="$SETTINGS"
EOF
