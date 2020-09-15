'''
A simple traffic utility which starting standalone TCP/UDP client/servers.

USAGE:
---------
# Start TCP Server on port 5649
$ python -mgrus.utils.traffic -t -v -s -p localhost 5649

# Start TCP Client to send ping to above server.
$ python -mgrus.utils.traffic -t -v -c -p localhost 5649
'''

import argparse

from grus.traffic import client as hclient
from grus.traffic import server as hserver

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-s', '--server', action="store_true",
        help="Run server")
    parser.add_argument(
        '-c', '--client', action="store_true",
        help="Run client")
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
        print ("Invalid host/port")
        raise

    def ping_handler(payload, data):
        if payload == data:
            print ("Success : Sent: %s , received: %s" % (payload, data))
        else:
            print ("Failure : Sent: %s , received: %s" % (payload, data))

    if args.server:
        server(port=port, verbose=verbose).start()
    else:
        client(server=host, port=port, verbose=verbose,
               handler=ping_handler).start(tries=10)


if __name__ == '__main__':
    main()