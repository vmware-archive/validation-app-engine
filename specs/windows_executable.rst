Purpose -
=========

This add rpyc_win_service.py effectively under axon/controller/ and is intended to
daemonize axon service for windows.

Prerequisit -
=============
Python must be there in System Path.
pywin32 must be installed on windows machine

Usage -
=======
  exe Creation Method 1 - (Creating exe using pip install)
-----------------------------------------------------------
    a. Create a pip installable on your runner machine using below command -
        $cd axon/
        $python pypi_packer.py

        This will create a pypi axon package and copy it in /var/lib/pypi/packages on runner

    b. Start pypi local server on runner using below command - (provided pypi server is installed on runner)
        $pypi-server -p 9000 /var/lib/pypi/packages &

    c. Now go on windows machine and insatll above pypi package using pip -
        > pip install axon --trusted-host 192.168.1.4 --index-url=http://192.168.1.4:9000
        where 192.168.1.4 is runner IP

    d. This will create a exe named 'axon_service.exe' in C:\Python27\Scripts\

  exe Creation Method 2 - (Creating exe from pyinstaller)
---------------------------------------------------------
    a. Install pyinstaller on windows machine
        > C:\Python27\Scripts\pip.exe install pyinstaller
    b.  > cd C:\Users\Administrator\Downloads
    c.  > Clone Axon source code on a windows machine.
    d.  > C:\Python27\Scripts\pyinstaller.exe --onefile axon\controller\windows\rpyc_win_service.py
    e. This will create an exe named axon_win_service.exe in same folder.

  Final usage to operate on service after exe creation -
-------------------------------------
    > axon_service.exe --help
    > axon_service.exe install # This will register service in task manager
    > axon_service.exe start   # This will start service (Visible in task manager)

    To confirm service start check from powershell using netstat-
        PS C:\Users\Administrator> NETSTAT.EXE -ano | grep 5678
          TCP    0.0.0.0:5678           0.0.0.0:0              LISTENING       3816

    Here service is started on port 5678

    > axon_service.exe stop # This will stop service (Visibe in tsk manager)
    > axon_service.exe remove # This will unregister axon service from task manager
