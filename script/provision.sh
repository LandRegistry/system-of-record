#This provision script doesn't currently run.  Just listing what I did to create
#the environment for System of Record.

#Add pip3 to the sudo path:
#sudo -i echo "export PATH=$PATH:/usr/local/bin" > /etc/profile.d/local_bin.sh

#install app requirements
#sudo -i pip3 install -r /vagrant/requirements.txt

#install postgres
#followed these intructions: https://wiki.postgresql.org/wiki/YUM_Installation
#used the rpm below:
#sudo -i yum localinstall http://yum.postgresql.org/9.4/redhat/rhel-7-x86_64/pgdg-centos94-9.4-1.noarch.rpm
#yum list postgres*
#sudo -i yum install postgresql94-server
#sudo -i /usr/pgsql-9.4/bin/postgresql94-setup initdb
#sudo -i service postgresql-9.4 start
#To login to psql 1) sudo - i 2) sudo -u postgres psql

