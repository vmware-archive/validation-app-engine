#!/usr/bin/env python
# Copyright (c) 2020 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.
'''
A simple traffic utility which starting standalone TCP/UDP client/servers.

USAGE:
---------
# Start TCP Server on port 5649
$ python -mjasper.utils.traffic -t -v -s -p localhost 5649

# Start TCP Client to send ping to above server.
$ python -mjasper.utils.traffic -t -v -c -p localhost 5649
'''

import argparse

from jasper.traffic import client as hclient
from jasper.traffic import server as hserver
from jasper.utils.common import is_py3


def _print(msg):
    if is_py3():
        print(msg)
    else:
        print msg


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-s', '--server', action="store_true",
        help="Run server")
    parser.add_argument(
        '-c', '--client', action="store_true",
        help="Run client")
    parser.add_argument(
        '-i', '--ipv6', action="store_true",
        help="Use IPv6 client / servers.")
    parser.add_argument(
        '-p', '--port', nargs='+',
        help="Port to connect")
    parser.add_argument(
        '-t', '--tcp', action="store_true",
        help="Run TCP traffic.")
    parser.add_argument(
        '-u', '--udp', action="store_true",
        help="Run UDP traffic.")
    parser.add_argument(
        '-v', '--verbose', action="store_true",
        help="Verbose mode")

    args = parser.parse_args()

    verbose = bool(args.verbose)

    client, server = None, None

    if args.tcp:
        client, server = hclient.TCPClient, hserver.TCPServer
    elif args.udp:
        client, server = hclient.UDPClient, hserver.UDPServer

    assert(args.port)
    try:
        host = args.port[0]
        port = int(args.port[1])
    except Exception:
        _print("Invalid host/port")
        raise

    def ping_handler(payload, data):
        if payload == data:
            _print("Success : Sent: %s , received: %s" % (payload, data))
        else:
            _print("Failure : Sent: %s , received: %s" % (payload, data))

    if args.server:
        ipv6 = args.ipv6
        server(port=port, verbose=verbose, ipv6=ipv6).start()
    else:
        client(server=host, port=port, verbose=verbose,
               handler=ping_handler).start(tries=10)


if __name__ == '__main__':
    main()