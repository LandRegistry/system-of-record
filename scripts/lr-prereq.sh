yum install -y python-devel

wget http://python.org/ftp/python/3.4.1/Python-3.4.1.tar.xz

tar xvf Python-3.4.1.tar.xz

cd Python-3.4.1

sudo ./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
sudo make
sudo make altinstall

pip install -r /vagrant/code/system-of-record/requirements.txt
