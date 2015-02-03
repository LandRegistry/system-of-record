echo "export PATH=$PATH:/usr/local/bin" > /etc/profile.d/local_bin.sh

echo "export SETTINGS=config.DevelopmentConfig" >> /home/vagrant/.bashrc

source /etc/profile.d/local_bin.sh

#install app requirements
pip3 install -r /vagrant/requirements.txt

#------------install puppet
gem install --no-ri --no-rdoc librarian-puppet puppet

cd /vagrant

librarian-puppet install --verbose
