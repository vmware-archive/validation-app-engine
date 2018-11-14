import contextlib
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
                conn.run(remote_cmd)
            elif isinstance(remote_cmd, list):
                for cmd in remote_cmd:
                    conn.run(remote_cmd)

    def remote_put_file(self, source, dest=None):
        """
        Copy source file to remote machine
        :param source: source file full path
        :param dest: destination location to copy
        :return: Operation success
        """
        # Observation: dest doesn't work in Windows
        with self.remote_connection() as conn:
            if dest:
                conn.put(source, dest)
            else:
                conn.put(source)

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
    def remote_install_sdist(self, sdist_package_path,
                             python_folder='Python27'):
        """
        Remotely upload previously created axon_service.exe from local host
        to remote host.
        :param sdist_package_path: python sdist tar.gz package

             This is created using -
               # python setup.py sdist
             This will create a tar.gz file in axon/dist/ directory
             wit same something like vmware-axon*

        :param python_folder: Python27 or Python34 etc
        :return: None
        """
        filename = os.path.basename(sdist_package_path)
        with self.remote_connection() as conn:
            # In case service is already running, we have to stop that
            # TODO(raies): Need to implement in clean way later
            try:
                self.remote_stop_axon()
            except Exception:
                pass
            conn.put(sdist_package_path)
            install_cmd = 'pip.exe install C:\\%homepath%\\' + filename
            conn.run(install_cmd)

    def remote_install_requirements(self, requirement_file,
                                    python_dir='Python27'):
        """
        Remotely uninstall given pypi packages from a requirement file
        :param pypi package name i.e. 'vmware-axon'
        :return: Operation success
        """
        # Set env vars with separate connection to make it effective
        homepath = 'setx /M Path "\%Path\%; C:\\%homepath%"'
        self.remote_run_command(homepath)

        with self.remote_connection() as conn:
            pre_packages = ["certifi", "pywin32"]
            for pre_package in pre_packages:
                run_pre_cmd = "pip.exe install %s" % pre_package
                conn.run(run_pre_cmd)

            filename = os.path.basename(requirement_file)
            conn.put(requirement_file)
            dest_file = 'C:\\%homepath%\\' + filename
            install_cmd = "pip.exe install -r %s" % dest_file
            if self.pypi_server and self.pypi_server_port:
                install_cmd = (install_cmd + " --trusted-host %s "
                               "--extra-index-url http://%s:%s" % (
                                   self.pypi_server,
                                   self.pypi_server,
                                   self.pypi_server_port))
            conn.run(install_cmd)

    def remote_register_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely register axon as a service
        :return: Operation success
        """
        register_cmd = "%s install" % axon_exe
        self.remote_run_command(register_cmd)

    def remote_start_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely start axon service
        :return: Operation success
        """
        start_cmd = "%s start" % axon_exe
        with self.remote_connection() as conn:
            conn.run('if not exist "C:\\axon" mkdir C:\\axon')
            conn.run(start_cmd)

    def remote_stop_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely stop axon service
        :return: Operation success
        """
        stop_cmd = "%s stop" % axon_exe
        self.remote_run_command(stop_cmd)

    def remote_restart_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely restart axon service
        :return: Operation success
        """
        restart_cmd = "%s restart" % axon_exe
        self.remote_run_command(restart_cmd)

    def remote_unregister_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely unregister axon service
        :return: Operation success
        """
        remove_cmd = "%s remove" % axon_exe
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
    def remote_install_sdist(self, sdist_package_path,
                             python_folder='Python27'):
        """
        Remotely upload previously created axon_service.exe from local host
        to remote host.
        :param sdist_package_path: python sdist tar.gz package
        :param python_folder: Python27 or Python34 etc
        :return: None
        """
        filename = os.path.basename(sdist_package_path)
        with self.remote_connection() as conn:
            # In case service is already running, we have to stop that
            # TODO(raies): Need to implement in clean way later
            try:
                self.remote_stop_axon()
            except Exception:
                pass
            conn.put(sdist_package_path, '/tmp')
            install_cmd = 'pip install /tmp/' + filename
            conn.run(install_cmd)

    def remote_install_requirements(self, requirement_file, dest="/tmp/"):
        """
        Remotely uninstall given pypi packages from a requirement file
        :param pypi package name i.e. 'vmware-axon'
        :return: Operation success
        """
        with self.remote_connection() as conn:
            pre_packages = ["certifi"]
            for pre_package in pre_packages:
                run_pre_cmd = "pip install %s" % pre_package
                conn.run(run_pre_cmd)

            filename = os.path.basename(requirement_file)
            conn.put(requirement_file, dest)
            dest_file = dest + "/" + filename
            install_cmd = "pip install -r %s" % dest_file
            if self.pypi_server and self.pypi_server_port:
                install_cmd = (install_cmd + " --trusted-host %s "
                               "--extra-index-url http://%s:%s" % (
                                   self.pypi_server,
                                   self.pypi_server,
                                   self.pypi_server_port))
            conn.run(install_cmd)

    def remote_install_debian(self, deb_package_path):
        """
        Remotely upload previously created axon deb from local host
        to remote host.
        :param deb_package_path: Full path of debian package
               i.e. '/tmp/test_axon.deb'
        :return: None
        """
        filename = os.path.basename(deb_package_path)
        with self.remote_connection() as conn:
            conn.put(deb_package_path, '/tmp')
            conn.run('cd /tmp/ && sudo dpkg -i %s' % filename)

    def remote_reload_daemon(self):
        """
        Remotely reload daemon.
        :return: None
        """
        reload_cmd = "sudo systemctl daemon-reload"
        self.remote_run_command(reload_cmd)
        with self.remote_connection() as conn:
            conn.run(reload_cmd)

    def remote_start_axon(self):
        """
        Remotely start axon service.
        :return: None
        """
        start_cmd = "sudo systemctl start axon"
        self.remote_run_command(start_cmd)

    def remote_stop_axon(self):
        """
        Remotely stop axon service.
        :return: None
        """
        stop_cmd = "sudo systemctl stop axon"
        self.remote_run_command(stop_cmd)

    def remote_restart_axon(self):
        """
        Remotely restart axon service.
        :return: None
        """
        restart_cmd = "sudo systemctl restart axon"
        self.remote_run_command(restart_cmd)

    def remote_status_axon(self):
        """
        Remotely status axon service.
        :return: None
        """
        status_cmd = "sudo systemctl status axon"
        self.remote_run_command(status_cmd)


if __name__ == "__main__":
    remote_password = "Admin!Admin1998"
    axn = AxonRemoteOperationLinux('15.27.10.161',
                                   remote_user='ubuntu',
                                   gw_host='10.59.84.202',
                                   gw_user='ubuntu',
                                   remote_password=remote_password)

    axn.remote_run_command('pip install pip --upgrade')
