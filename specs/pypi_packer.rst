Purpose -
=========

This adds packer.py in the top directory and is intended to create a axon package
and upload to pypi server (currently to the localhost i.e. runner in this case)
With respect to each given version, it will create a python packge under dist
directory and then upload to pypi package container path.

Usage -
=======

python pypi_packer.py --server <pypi server address> --path <full path of package container in pypi server>

for example, if path is /root/packages,
a created package with the name "axon_<version>" will be created and uploaded to /root/packages.

Prerequisit -
=============
pypi server should be running on a given port on given host.

How to install local pypii server ?
===================================
  pip install pypiserver
  mkdir /var/lib/pypi/packages
  pypi-server -p 9000 /var/lib/pypi/packages &

This will start pypiserver on port 9000 and /var/lib/pypi/packages will work as package container.

How to install this package on remote machine ?
==============================================

Assumption -
  pypi server is running on given address and path is correct
  pypi server is accessible from remote machine
  package container directory should be accessible from remote machine

Installation -
  pip install axon --trusted-host <pypi server IP> --index-url=http://<pypi server IP>:<pypi server port>

  for example -
  pip install axon --trusted-host 192.168.1.4 --index-url=http://192.168.1.4:9000

  or

  pip install axon --trusted-host 192.168.1.4 --extra-index-url=http://192.168.1.4:9000

  even this extra index url can be added in pip.conf of package consuming host.

Conclusion -
============

This will install axon in remote machine environment.

Consumption -
============
If pythonpath and related environments are correct, we can directly import axon and start using it.
For example -

  import axon
  from axon.traffic.servers import servers

  t_server = servers.ThreadedTCPServer()
  t_server.run()
