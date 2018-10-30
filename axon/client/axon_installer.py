import os

from fabric import Connection
from functools import wraps

# These can be removed when password less is working
remote_password = 'VMware@123'
gateway_password = "!cisco"


def fab_remote_connector(func):
    """
    Fabic Connection decorator to create remote connection (via gateway
    if required) and executes remote commands.
    :param func:
    :return: wrapper method
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            (gw_host, gw_user, remote_host,
             remote_user, remote_cmd) = func(*args, **kwargs)
            gateway = None
            if gw_host:
                gateway = Connection(
                    gw_host,
                    user=gw_user,
                    connect_kwargs={"password": gateway_password})
            with Connection(remote_host, user=remote_user,
                            gateway=gateway,
                            connect_kwargs={"password": remote_password})\
                    as conn:
                    print("remote_cmd", remote_cmd)
                    conn.run(remote_cmd)
        except Exception as e:
            raise RuntimeError(e)
        else:
            print("Operation Successful.")
    return wrapped


class AxonRemoteOperation(object):
    """
    Base class for all Axon(Windows/Linux) operations.
    """
    def __init__(self, remote_host, remote_user=None,
                 gw_host=None, gw_user=None,
                 pypi_server=None, pypi_server_port=None):
        """
        :param remote_host: Remote host where operation is needs to
                            be performed.
        :param remote_user: Remote host username to connect with.
        :param gw_host: Gateway host
        :param gw_user: Gateway username
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

    @fab_remote_connector
    def remote_install_pypi(self, pypi_package):
        """
        Remotely install given pypi package
        :param pypi_package: pypi package name i.e. 'vmware-axon'
        :return: Operation success
        """
        install_cmd = "%s install %s --trusted-host %s "\
            "--extra-index-url http://%s:%s" % (
                self.pip_map[os.name], pypi_package, self.pypi_server,
                self.pypi_server, self.pypi_server_port)
        return (self._gw_host, self._gw_user,
                self._host, self._username, install_cmd)

    @fab_remote_connector
    def remote_uninstall_pypi(self, pypi_package):
        """
        Remotely uninstall given pypi package
        :param pypi package name i.e. 'vmware-axon'
        :return: Operation success
        """
        uninstall_cmd = "%s uninstall -y %s" % (
            self.pip_map[os.name], pypi_package)
        return (self._gw_host, self._gw_user,
                self._host, self._username, uninstall_cmd)


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

    def remote_install_exe(self, exe_package_path, python_folder='Python27'):
        """
        Remotely upload previously created axon_service.exe from local host
        to remote host.
        :param exe_package_path:
        :param python_folder:
        :return: None
        """
        gateway = None
        if self._gw_host:
            gateway = Connection(
                self._gw_host, user=self._gw_user,
                connect_kwargs={"password": gateway_password})
        with Connection(self._host,
                        user=self._username,
                        gateway=gateway,
                        connect_kwargs={"password": remote_password}) as conn:
            # This will copy file from source to remote's HOME folder
            conn.put(exe_package_path)

            source = '%homepath%' + '\\' + 'axon_service.exe'
            # Destination must be Python's Scripts path
            destination = "C:\%s\Scripts" % python_folder
            copy_cmd = 'cp %s %s' % (source, destination)
            conn.run(copy_cmd)

    @fab_remote_connector
    def remote_register_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely register axon as a service
        :return: Operation success
        """
        register_cmd = "%s install" % axon_exe
        return (self._gw_host, self._gw_user,
                self._host, self._username, register_cmd)

    @fab_remote_connector
    def remote_start_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely start axon service
        :return: Operation success
        """
        start_cmd = "%s start" % axon_exe
        return (self._gw_host, self._gw_user,
                self._host, self._username, start_cmd)

    @fab_remote_connector
    def remote_stop_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely stop axon service
        :return: Operation success
        """
        stop_cmd = "%s stop" % axon_exe
        return (self._gw_host, self._gw_user,
                self._host, self._username, stop_cmd)

    @fab_remote_connector
    def remote_restart_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely restart axon service
        :return: Operation success
        """
        restart_cmd = "%s restart" % axon_exe
        return (self._gw_host, self._gw_user,
                self._host, self._username, restart_cmd)

    @fab_remote_connector
    def remote_unregister_axon(self, axon_exe='axon_service.exe'):
        """
        Remotely unregister axon service
        :return: Operation success
        """
        remove_cmd = "%s remove" % axon_exe
        return (self._gw_host, self._gw_user,
                self._host, self._username, remove_cmd)


class AxonRemoteOperationLinux(AxonRemoteOperation):
    """
    This class implements remote operations for Linux -
    Remote operations implemented are -
        - upload debian file from local to remote
        - Starts axon service remotely.
        - Stops axon service remotely.
        - Restart axon service remotely.
    """
    def remote_install_debian(self, deb_package_path):
        """
        Remotely upload previously created axon deb from local host
        to remote host.
        :param deb_package_path: Full path of debian package
               i.e. '/tmp/test_axon.deb'
        :return: None
        """
        filename = os.path.basename(deb_package_path)
        gateway = None
        if self._gw_host:
            gateway = Connection(self._gw_host,
                                 user=self._gw_user,
                                 connect_kwargs={"password": gateway_password})
        with Connection(self._host,
                        user=self._username,
                        gateway=gateway,
                        connect_kwargs={"password": remote_password}) as conn:
            conn.put(deb_package_path, '/tmp')
            conn.run('cd /tmp/ && sudo dpkg -i %s' % filename)

    @fab_remote_connector
    def remote_reload_daemon(self):
        """
        Remotely reload daemon.
        :return: None
        """
        reload_cmd = "systemctl daemon-reload"
        return (self._gw_host, self._gw_user,
                self._host, self._username, reload_cmd)

    @fab_remote_connector
    def remote_start_axon(self):
        """
        Remotely start axon service.
        :return: None
        """
        start_cmd = "systemctl start axon"
        return (self._gw_host, self._gw_user,
                self._host, self._username, start_cmd)

    @fab_remote_connector
    def remote_stop_axon(self):
        """
        Remotely stop axon service.
        :return: None
        """
        stop_cmd = "systemctl stop axon"
        return (self._gw_host, self._gw_user,
                self._host, self._username, stop_cmd)

    @fab_remote_connector
    def remote_restart_axon(self):
        """
        Remotely restart axon service.
        :return: None
        """
        restart_cmd = "systemctl restart axon"
        return (self._gw_host, self._gw_user,
                self._host, self._username, restart_cmd)

    @fab_remote_connector
    def remote_status_axon(self):
        """
        Remotely status axon service.
        :return: None
        """
        status_cmd = "systemctl status axon"
        return (self._gw_host, self._gw_user,
                self._host, self._username, status_cmd)


if __name__ == "__main__":
    """
    Assumption:
      For method 1 windows :
        - pypi server is running on given pypi server ip and port
        - pip package is present on pypi server(s)
    """
    axn = AxonRemoteOperationWindows('10.112.156.43',
                                     remote_user='raies',
                                     pypi_server='10.172.51.73',
                                     pypi_server_port=9000)
    # Method 1 Windows -
    # pywin32 must be installed for axon operations on windows
    for package in ['pywin32', 'vmware-axon']:
        axn.remote_install_pypi(package)

    # or Method 2 Windows - (Use only method 1 or method 2)
    # axn.remote_install_exe('/tmp/axon_service.exe')
    import time
    axn.remote_register_axon()
    time.sleep(2)
    axn.remote_start_axon()
    time.sleep(2)
    axn.remote_stop_axon()
    time.sleep(2)
    axn.remote_unregister_axon()
    time.sleep(2)
    axn.remote_uninstall_pypi('vmware-axon')
    time.sleep(2)


    def install(host):
        installer = AxonRemoteOperationLinux(
            host, remote_user='ubuntu',
            gw_host='10.59.84.167', gw_user='ubuntu')
        installer.remote_install_debian('/root/axon/debian/dist/test_axon.deb')
