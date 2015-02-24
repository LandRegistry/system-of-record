echo "export PATH=$PATH:/usr/local/bin" > /etc/profile.d/local_bin.sh

echo "export SETTINGS=config.DevelopmentConfig" >> /home/vagrant/.bashrc

source /etc/profile.d/local_bin.sh

#------------install puppet
gem install --no-ri --no-rdoc puppet

#------------install postgres module
puppet module install puppetlabs-postgresql

#------------install and configure postgres
puppet apply /vagrant/manifests/postgres.pp


puppet module install garethr-erlang

puppet apply /vagrant/manifests/erlang.pp

puppet module install puppetlabs-rabbitmq

puppet apply /vagrant/manifests/rabbit.pp

gem install --no-ri --no-rdoc foreman

cd /vagrant

source environment.sh
#Run install script for system of record
source install.sh
