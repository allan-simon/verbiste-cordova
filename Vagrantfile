# -*- mode: ruby -*-
# vi: set ft=ruby ts=2 sw=2 expandtab :


# in order to setup the communication between your computer
# and your phone, expo-cli will expose the LAN ip of your computer
# on a computer.
# However when running from within docker, expo-cli has only access
# to the docker container own ip address (not accessible from outside)
# so to work around that, as the vagrantfile code is run on the host
# we get from here the ip that we then give to the container using
# vagrant provisionning
require 'socket'
ip_address = Socket.ip_address_list.find { |ai| ai.ipv4? && !ai.ipv4_loopback? }.ip_address

PROJECT = "verbiste_cordova"

ENV['VAGRANT_NO_PARALLEL'] = 'yes'
ENV['VAGRANT_DEFAULT_PROVIDER'] = 'docker'
Vagrant.configure(2) do |config|

  config.ssh.insert_key = false
  config.vm.define "dev", primary: true do |app|
    app.vm.provider "docker" do |d|
      d.image = "allansimon/docker-dev-js"

      d.name = "#{PROJECT}_dev"

      d.has_ssh = true
      d.env = {
        "HOST_USER_UID" => Process.euid,
      }
    end
    app.ssh.username = "vagrant"

    app.vm.provision "install_expo", type: "shell", privileged: false do |s|
      s.inline = "
        sudo npm install --global cordova

        echo 'cd /vagrant' >> /home/vagrant/.zshrc "
    end

  end
end
