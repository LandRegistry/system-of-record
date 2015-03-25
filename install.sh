#!/bin/bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir

virtualenv -p python3 ~/venvs/system-of-record
source ~/venvs/system-of-record/bin/activate
if [ -d /usr/pgsql-9.3/bin ]; then
  export PATH=$PATH:/usr/pgsql-9.3/bin
fi
pip install -r requirements.txt

#Create the logging directory as it is required by default
if [ ! -d $dir/logs ]; then
	mkdir $dir/logs
fi

#Set environment variable in supervisord according to deploying environment (default to development)
case "$DEPLOY_ENVIRONMENT" in
  development)
  SUPERVISOR_ENV="SETTINGS=\"config.DevelopmentConfig\""
  ;;
  preview)
  SUPERVISOR_ENV="SETTINGS=\"config.PreviewConfig\""
  ;;
  preproduction)
  SUPERVISOR_ENV="SETTINGS=\"config.PreproductionConfig\""
  ;;
  production)
  SUPERVISOR_ENV="SETTINGS=\"config.ProductionConfig\""
  ;;
  *)
  SUPERVISOR_ENV="SETTINGS=\"config.DevelopmentConfig\""
  ;;
esac

#Run manage with appropriate SETTINGS variable from above
eval `echo $SUPERVISOR_ENV` python manage.py db upgrade

if [ -n "$SQLALCHEMY_DATABASE_URI" ]; then
  SUPERVISOR_ENV="$SUPERVISOR_ENV,SQLALCHEMY_DATABASE_URI=\"$SQLALCHEMY_DATABASE_URI\""
fi

if [ -n "$RABBIT_ENDPOINT" ]; then
  SUPERVISOR_ENV="$SUPERVISOR_ENV,RABBIT_ENDPOINT=\"$RABBIT_ENDPOINT\""
fi

if [ -n "$RABBIT_QUEUE" ]; then
  SUPERVISOR_ENV="$SUPERVISOR_ENV,RABBIT_QUEUE=\"$RABBIT_QUEUE\""
fi

if [ -n "$RABBIT_ROUTING_KEY" ]; then
  SUPERVISOR_ENV="$SUPERVISOR_ENV,RABBIT_ROUTING_KEY=\"$RABBIT_ROUTING_KEY\""
fi

if [ -n "$LOGGING_PATH" ]; then
  SUPERVISOR_ENV="$SUPERVISOR_ENV,LOGGING_PATH=\"$LOGGING_PATH\""
fi

echo "Adding system of record to supervisord..."
cat > /etc/supervisord.d/systemofrecord.ini << EOF
[program:systemofrecord]
command=$HOME/venvs/system-of-record/bin/gunicorn --log-file=- --log-level DEBUG -b 0.0.0.0:5001 --timeout 120 application.server:app
directory=$dir
autostart=true
autorestart=true
user=$USER
environment=$SUPERVISOR_ENV
EOF
