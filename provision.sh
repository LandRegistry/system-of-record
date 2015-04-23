#!/bin/bash

echo "export PATH=$PATH:/usr/local/bin" > /etc/profile.d/local_bin.sh

source /etc/profile.d/local_bin.sh

yum install -y python-devel
pip install virtualenv
pip install virtualenvwrapper

echo "Configure virtualenvwrapper..."
cat >> /home/vagrant/.bashrc << EOF
  export WORKON_HOME='/home/vagrant/venvs'
  source /usr/bin/virtualenvwrapper.sh
EOF

gem install --no-ri --no-rdoc puppet:3.7.5

puppet module install puppetlabs-apt --version "<2.0.0"

puppet module install puppetlabs-postgresql

puppet apply /home/vagrant/srv/system-of-record/manifests/postgres.pp

puppet module install garethr-erlang

puppet apply /home/vagrant/srv/system-of-record/manifests/erlang.pp

puppet module install puppetlabs-rabbitmq

puppet apply /home/vagrant/srv/system-of-record/manifests/rabbit.pp
