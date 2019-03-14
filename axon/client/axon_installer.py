#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import contextlib
import logging
import os

from fabric import Connection


class AxonRemoteOperation(object):
    """
    Base class for all Axon(Windows/Linux) operations.
    """
    def __init__(self, remote_host, remote_user=None, remote_password=None,
                 gw_host=None, gw_user=None, gw_password=None,
                 pypi_server=None, pypi_server_port=None):
        """
        :param remote_host: Remote host where operation is needs to
                            be performed.
        :param remote_user: Remote host username to connect with.
        :param remote_user: Remote host password to connect with..
        :param gw_host: Gateway host
        :param gw_user: Gateway username
        :param gw_user: Gateway password
        :param pypi_server: Pypi server IP
        :param pypi_server_port: Pypi server port
        """
        self.log = logging.getLogger(__name__)
        self._host = remote_host
        self._username = remote_user
        self._gw_host = gw_host
        self._gw_user = gw_user
        self.pypi_server = pypi_server
        self.pypi_server_port = pypi_server_port
        self.pip_map = {'posix': 'pip', 'nt': 'pip.exe'}
        self.connect_kwargs_remote = {}
        self.connect_kwargs_gateway = {}
        if remote_password:
            self.connect_kwargs_remote = {"password": remote_password}
        if gw_password:
            self.connect_kwargs_gateway = {"password": gw_password}

    @contextlib.contextmanager
    def remote_connection(self):
        """
        Remote connection context manager
        """
        gateway = None
        if self._gw_host:
            gateway = Connection(
                self._gw_host,
                user=self._gw_user,
                connect_kwargs=self.connect_kwargs_gateway)
        conn = Connection(self._host, user=self._username,
                          gateway=gateway,
                          connect_kwargs=self.connect_kwargs_remote)
        self.log.info("Connection is created successfully.")
        try:
            yield conn
        finally:
            conn.close()

    def remote_run_command(self, remote_cmd):
        """
        Run given command on remote machine
        :param remote_cmd: remote commmand to run
        :return: Operation success
        """
        with self.remote_connection() as conn:
            if isinstance(remote_cmd, str):
                self.log.info("Running remote command - %s" % remote_cmd)
                conn.run(remote_cmd)
                self.log.info("Remote command successful - %s" % remote_cmd)
            elif isinstance(remote_cmd, list):
                for cmd in remote_cmd:
                    self.log.info("Running remote command - %s" % cmd)
                    conn.run(remote_cmd)
                    self.log.info("Remote command successful - %s" % cmd)

    def remote_put_file(self, source, dest=None):
        """
        Copy source file to remote machine
        :param source: source file full path
        :param dest: destination location to copy
        :return: Operation success
        """
        # Observation: dest doesn't work in Windows

        self.log.info("Check for source file existance..")
        if not os.path.exists(source):
            self.log.exception("source '%s' doesn't exists" % source)
            raise RuntimeError

        with self.remote_connection() as conn:
            self.log.info("copy file..")
            if dest:
                conn.put(source, dest)
            else:
                conn.put(source)
            self.log.info("File copy is successful")

    def remote_install_pypi(self, pypi_package, remote_os_name='posix'):
        """
        Remotely install given pypi package
        :param pypi_package: pypi package name i.e. 'vmware-axon'
        :return: Operation success
        """
        install_cmd = ("%s install %s" % (
                       self.pip_map[remote_os_name], pypi_package))
        if self.pypi_server and self.pypi_server_port:
            install_cmd = (install_cmd + " --trusted-host %s "
                           "--extra-index-url http://%s:%s" % (
                               self.pypi_server,
                               self.pypi_server,
                               self.pypi_server_port))
        self.remote_run_command(install_cmd)

    def remote_uninstall_pypi(self, pypi_package):
        """
        Remotely uninstall given pypi package
        :param pypi package name i.e. 'vmware-axon'
        :return: Operation success
        """
        uninstall_cmd = "%s uninstall -y %s" % (
            self.pip_map[os.name], pypi_package)
        self.remote_run_command(uninstall_cmd)


class AxonRemoteOperationWindows(AxonRemoteOperation):
    """
    Assumption -
        - axon is pip based implementation so that axon_service.exe will
          present in python scripts path.
        - pypi server is running on specified host and port.
        - pypi package is present on pypi packages directory.
        - ssh server is running on remote windows machine on default port 22

    This class implements remote operations for windows -
    Remote operations implemented are -
        - upload exe file from local to remote
        - Register axon as a service in windows remotely.
        - Starts axon service remotely.
        - Stops axon service remotely.
        - Unregisters axon service remotely.

    Important -
        To use this there will always be two methods -
            1. Install vmware-axon pip package and then perform
               Register/Start/Stop/Unregister operations

               i.e -

               $ axn = AxonRemoteOperationWindows((**params)
               $ axn.remote_install_pypi('vmware-axon')
               $ axn.remote_register_axon()
               $ ... and so on

            2. Upload exe from local machine to remote machine's python
               scripts path, and then perform Register/Start/Stop/Unregister
               operations

               i.e -

               $ axn = AxonRemoteOperationWindows((**params)
               Assume axon_service.exe is put in /tmp/ in local machine
               $ axn.remote_install_exe('/tmp/axon_service.exe')
               $ axn.remote_register_axon()
               $ ... and so on

        At a time only one of above procedure needs to be followed.

    """
    def remote_install_sdist(self, sdist_package_path):
        """
        Remotely upload previously created axon_service.exe from local host
        to remote host.
        :param sdist_package_path: python sdist tar.gz package

             This is created using -
               # python setup.py sdist
             This will create a tar.gz file in axon/dist/ directory
             wit same something like vmware-axon*
        :return: None
        """
        if not os.path.exists(sdist_package_path):
            self.log.exception("path '%s' doesn't exist." % sdist_package_path)
            raise RuntimeError
        filename = os.path.basename(sdist_package_path)
        with self.remote_connection() as conn:
            self.log.info("Installing pywin32 in remote windows machine.")
            conn.run('pip.exe install pywin32')
            self.log.info('Installation successful !!')
            # In case service is already running, we have to stop that
            try:
                self.remote_stop_axon()
            except Exception:
                pass
            self.log.info('copy sdist package to remote machine.')
            conn.put(sdist_package_path)
            self.log.info('Package copy successful !!')
            install_cmd = 'pip.exe install C:\\%homepath%\\' + filename
            self.log.info("Installing axon on remote windows machine.")
            conn.run(install_cmd)
            self.log.info('Installation successful !!')

    def remote_install_requirements(self, requirement_file):
        """
        Remotely uninstall given pypi packages from a requirement file
        :param pypi package name i.e. 'vmware-axon'
        :return: Operation success
        """
        if not os.path.exists(requirement_file):
            self.log.exception("Path '%s' doesn't exist." % requirement_file)
            raise RuntimeError
        with self.remote_connection() as conn:
            pre_packages = ["pywin32"]
            for pre_package in pre_packages:
                self.log.info("Installing pywin32 in remote windows machine.")
                run_pre_cmd = "pip.exe install %s" % pre_package
                conn.run(run_pre_cmd)
                self.log.info('Installation successful !!')

            filename = os.path.basename(requirement_file)

            self.log.info('copy requirements file  to remote machine.')
            conn.put(requirement_file)
            self.log.info('Package copy successful !!')
            dest_file = 'C:\\%homepath%\\' + filename
            install_cmd = "pip.exe install -r %s" % dest_file
            if self.pypi_server and self.pypi_server_port:
                install_cmd = (install_cmd + " --trusted-host %s "
                               "--extra-index-url http://%s:%s" % (
                                   self.pypi_server,
                                   self.pypi_server,
                                   self.pypi_server_port))
            self.log.info("Installing requirements on remote machine.")
            conn.run(install_cmd)
            self.log.info('Installation successful !!')

    def remote_register_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely register axon as a service
        :return: Operation success
        """
        register_cmd = "%s --startup auto install" % axon_exe
        self.log.info("Registering axon service.")
        self.remote_run_command(register_cmd)

    def remote_start_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely start axon service
        :return: Operation success
        """
        start_cmd = "%s start" % axon_exe
        with self.remote_connection() as conn:
            conn.run('if not exist "C:\\axon" mkdir C:\\axon')
            self.log.info("starting axon service.")
            conn.run(start_cmd)

    def remote_stop_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely stop axon service
        :return: Operation success
        """
        stop_cmd = "%s stop" % axon_exe
        self.log.info("stoping axon service.")
        self.remote_run_command(stop_cmd)

    def remote_restart_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely restart axon service
        :return: Operation success
        """
        restart_cmd = "%s restart" % axon_exe
        self.log.info("Restarting axon service.")
        self.remote_run_command(restart_cmd)

    def remote_unregister_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely unregister axon service
        :return: Operation success
        """
        remove_cmd = "%s remove" % axon_exe
        self.log.info("Unregistering axon service.")
        self.remote_run_command(remove_cmd)


class AxonRemoteOperationLinux(AxonRemoteOperation):
    """
    This class implements remote operations for Linux -
    Remote operations implemented are -
        - upload debian file from local to remote
        - Starts axon service remotely.
        - Stops axon service remotely.
        - Restart axon service remotely.
    """
    def remote_install_sdist(self, sdist_package_path):
        """
        Remotely upload previously created axon_service.exe from local host
        to remote host.
        :param sdist_package_path: python sdist tar.gz package
        :return: None
        """
        if not os.path.exists(sdist_package_path):
            self.log.exception("path '%s' doesn't exist." % sdist_package_path)
            raise RuntimeError
        filename = os.path.basename(sdist_package_path)
        with self.remote_connection() as conn:
            # In case service is already running, we have to stop that
            try:
                self.remote_stop_axon()
            except Exception:
                pass

            self.log.info("copy file to remote machine.")
            conn.put(sdist_package_path, '/tmp')
            self.log.info("Copy successful")
            install_cmd = 'sudo -H pip install /tmp/' + filename
            self.log.info("Install sdist package to remote machine.")
            conn.run(install_cmd)
            self.log.info("Installation successful.")

    def remote_install_requirements(self, requirement_file, dest="/tmp"):
        """
        Remotely uninstall given pypi packages from a requirement file
        :param pypi package name i.e. 'vmware-axon'
        :return: Operation success
        """
        if not os.path.exists(requirement_file):
            self.log.exception("Path '%s' doesn't exist." % requirement_file)
            raise RuntimeError
        with self.remote_connection() as conn:
            # Prerequirements
            conn.run('sudo apt-get install python-setuptools -y --force-yes')
            conn.run('sudo apt-get install python-pip -y')
            conn.run('sudo -H pip install --upgrade pip setuptools')

            filename = os.path.basename(requirement_file)
            self.log.info("copy requirements file to remote machine.")
            conn.put(requirement_file, dest)
            self.log.info("Copy successful")
            dest_file = dest + "/" + filename
            install_cmd = "sudo -H pip install -r %s" % dest_file
            if self.pypi_server and self.pypi_server_port:
                install_cmd = (install_cmd + " --trusted-host %s "
                               "--extra-index-url http://%s:%s" % (
                                   self.pypi_server,
                                   self.pypi_server,
                                   self.pypi_server_port))
            self.log.info("Installing requirements on remote machine.")
            conn.run(install_cmd)
            self.log.info("Installation successful.")

    def remote_install_distribution(self, distribuion_package_path):
        """
        Remotely upload previously created axon deb from local host
        to remote host.
        :param distribuion_package_path: Full path of distribution package
               i.e. '/tmp/test_axon.deb' or /tmp/test_axon.rpm
        :return: None
        """
        if not os.path.exists(distribuion_package_path):
            msg = "path '%s' doesn't exist." % distribuion_package_path
            self.log.exception(msg)
            raise RuntimeError
        filename = os.path.basename(distribuion_package_path)

        # Derive os_type from installer package itself
        # <name>.'deb' -> debian based package
        # <name>.rpm -> rpm based package
        _installer_type = distribuion_package_path.split('.')[1]
        with self.remote_connection() as conn:
            self.log.info("copy dist file to remote machine.")
            conn.put(distribuion_package_path, '/tmp')
            self.log.info("Copy successful")

            self.log.info("Installing distribution on remote machine.")
            if _installer_type == 'deb':
                conn.run('cd /tmp/ && sudo dpkg -i %s' % filename)
                self.log.info("Installation successful.")
            elif _installer_type == 'rpm':
                conn.run('cd /tmp/ && sudo rpm -u %s' % filename)
                self.log.info("Installation successful.")
            else:
                self.log.exception("No valid dist (.rpm or .deb) found.")
                raise RuntimeError

    def remote_reload_daemon(self):
        """
        Remotely reload daemon.
        :return: None
        """
        reload_cmd = "sudo systemctl daemon-reload"
        self.log.info("Reload axon daemon")
        self.remote_run_command(reload_cmd)

    def remote_start_axon(self):
        """
        Remotely start axon service.
        :return: None
        """
        start_cmd = "sudo systemctl start axon"
        self.log.info("Start axon service.")
        self.remote_run_command(start_cmd)

    def remote_stop_axon(self):
        """
        Remotely stop axon service.
        :return: None
        """
        stop_cmd = "sudo systemctl stop axon"
        self.log.info("Stop axon service.")
        self.remote_run_command(stop_cmd)

    def remote_restart_axon(self):
        """
        Remotely restart axon service.
        :return: None
        """
        restart_cmd = "sudo systemctl restart axon"
        self.log.info("Restart axon service.")
        self.remote_run_command(restart_cmd)

    def remote_status_axon(self):
        """
        Remotely status axon service.
        :return: None
        """
        status_cmd = "sudo systemctl status axon"
        self.log.info("Get axon service status.")
        self.remote_run_command(status_cmd)


if __name__ == "__main__":
    remote_password = "my_password"
    axn_linux = AxonRemoteOperationLinux('1.2.3.4',
                                         remote_user='ubuntu',
                                         gw_host='1.2.3.5',
                                         gw_user='ubuntu',
                                         remote_password=remote_password)

    axn_win = AxonRemoteOperationWindows('2.3.4.5',
                                         remote_user='Administrator',
                                         gw_host='2.3.4.6',
                                         gw_user='ubuntu',
                                         remote_password=remote_password)
    # Axon on linux Steps-
    # 1. copy and install requirements.txt
    requirement_file = '/var/lib/automation/packages/axon_requirements.txt'
    axn_linux.remote_install_requirements(requirement_file)
    # 2. Install axon on ubuntu machine using debian
    debian_file = '/var/lib/automation/packages/axon_service.deb'
    axn_linux.remote_install_distribution(debian_file)

    # Axon on windows Steps.
    # 1. install using sdist distribution package
    tarball_file = '/var/lib/automation/packages/axon_service.tar.gz'
    # axn_win.remote_install_sdist(tarball_file)
    # 2. register service in service manager
    axn_win.remote_register_axon()
    # 3. start service
    axn_win.remote_start_axon()
