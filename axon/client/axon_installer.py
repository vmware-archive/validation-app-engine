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

    # For linux install -

    hosts = ['15.26.10.251', '15.26.10.248', '15.26.10.254', '15.26.10.252',
             '15.26.10.253', '15.26.10.233', '15.26.10.238', '15.26.10.239',
             '15.26.10.236', '15.26.10.237', '15.26.10.224', '15.26.10.225',
             '15.26.10.229', '15.26.10.242', '15.26.10.240', '15.26.10.241',
             '15.26.10.247', '15.26.10.244', '15.26.10.245', '15.26.10.235',
             '15.26.10.232', '15.26.10.216', '15.26.10.222', '15.26.10.223',
             '15.26.10.220', '15.26.10.221', '15.26.10.210', '15.26.10.211',
             '15.26.10.208', '15.26.10.163', '15.26.10.160', '15.26.10.161',
             '15.26.10.166', '15.26.10.167', '15.26.10.165', '15.26.10.218',
             '15.26.10.219', '15.26.10.204', '15.26.10.194', '15.26.10.195',
             '15.26.10.192', '15.26.10.198', '15.26.10.196', '15.26.10.197',
             '15.26.10.250', '15.26.10.209', '15.26.10.214', '15.26.10.215',
             '15.26.10.212', '15.26.10.202', '15.26.10.201', '15.26.10.206',
             '15.26.10.207', '15.26.10.125', '15.26.10.114', '15.26.10.115',
             '15.26.10.118', '15.26.10.80', '15.26.10.81', '15.26.10.86',
             '15.26.10.84', '15.26.10.85', '15.26.10.74', '15.26.10.75',
             '15.26.10.72', '15.26.10.37', '15.26.10.90', '15.26.10.88',
             '15.26.10.89', '15.26.10.95', '15.26.10.92', '15.26.10.93',
             '15.26.10.82', '15.26.10.65', '15.26.10.70', '15.26.10.68',
             '15.26.10.69', '15.26.10.122', '15.26.10.121', '15.26.10.127',
             '15.26.10.124', '15.26.10.73', '15.26.10.78', '15.26.10.79',
             '15.26.10.76', '15.26.10.77', '15.26.10.66', '15.26.10.67',
             '15.26.10.64', '15.26.10.131', '15.26.10.128', '15.26.10.135',
             '15.26.10.132', '15.26.10.133', '15.26.10.186', '15.26.10.187',
             '15.26.10.184', '15.26.10.139', '15.26.10.136', '15.26.10.137',
             '15.26.10.142', '15.26.10.143', '15.26.10.140', '15.26.10.141',
             '15.26.10.130', '15.26.10.183', '15.26.10.180', '15.26.10.181',
             '15.26.10.171', '15.26.10.168', '15.26.10.169', '15.26.10.174',
             '15.26.10.175', '15.26.10.185', '15.26.10.190', '15.26.10.191',
             '15.26.10.188', '15.26.10.178', '15.26.10.179', '15.26.10.177',
             '15.26.10.182', '15.26.10.109', '15.26.10.98', '15.26.10.99',
             '15.26.10.96', '15.26.10.102', '15.26.10.103', '15.26.10.101',
             '15.26.10.154', '15.26.10.119', '15.26.10.116', '15.26.10.106',
             '15.26.10.107', '15.26.10.104', '15.26.10.105', '15.26.10.110',
             '15.26.10.108', '15.26.10.147', '15.26.10.144', '15.26.10.145',
             '15.26.10.150', '15.26.10.151', '15.26.10.148', '15.26.10.149',
             '15.26.10.138', '15.26.10.155', '15.26.10.152', '15.26.10.153',
             '15.26.10.158', '15.26.10.159', '15.26.10.156', '15.26.10.157',
             '15.26.10.146', '15.26.10.162', '15.26.10.56', '15.26.10.62',
             '15.26.10.63', '15.26.10.61', '15.26.10.50', '15.26.10.40',
             '15.26.10.41', '15.26.10.44', '15.26.10.34', '15.26.10.32',
             '15.26.10.33', '15.26.10.38', '15.26.10.36', '15.26.10.51',
             '15.26.10.48', '15.26.10.49', '15.26.10.54', '15.26.10.55',
             '15.26.10.52', '15.26.10.42', '15.26.10.43', '15.26.10.27',
             '15.26.10.24', '15.26.10.25', '15.26.10.30', '15.26.10.31',
             '15.26.10.28', '15.26.10.29', '15.26.10.18', '15.26.10.26',
             '15.26.10.9', '15.26.10.14', '15.26.10.13', '15.26.10.7',
             '15.26.10.4', '15.26.10.5', '15.26.10.58', '15.26.10.59',
             '15.26.10.19', '15.26.10.16', '15.26.10.17', '15.26.10.22',
             '15.26.10.23', '15.26.10.20', '15.26.10.21', '15.26.10.8']

    def install(host):
        installer = AxonRemoteOperationLinux(
            host, remote_user='ubuntu',
            gw_host='10.59.84.167', gw_user='ubuntu')
        installer.remote_install_debian('/root/axon/debian/dist/test_axon.deb')

    for host in hosts:
        install(host)
