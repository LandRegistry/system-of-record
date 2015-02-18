# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.vm.box = "landregistry/centos-beta"
  config.vm.network "private_network", ip: "192.168.50.5"
  config.vm.provision :shell, :path => 'scripts/provision.sh'

end
