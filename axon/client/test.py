from axon.client.traffic_elements import TrafficRule, \
    Endpoint, Port, Protocol, Action
from axon.client.cloud_traffic_controller import CloudTrafficController


hosts = ['15.26.10.123', '15.26.10.131',
         '15.26.10.212', '15.26.10.28', '15.26.10.104']

rule_list = []
for index, host in enumerate(hosts):
    destinations = hosts[index + 1: len(hosts)] + hosts[0: index]
    for destination in destinations:
        rule_list.append(
            TrafficRule(Endpoint(host), Endpoint(destination),
                        Port(12345), Protocol.TCP, Action.ALLOW)
        )
        rule_list.append(
            TrafficRule(Endpoint(host), Endpoint(destination),
                        Port(12345), Protocol.UDP, Action.ALLOW)

        )

import time
start = time.time()
controller = CloudTrafficController(gateway_host='10.59.84.167')
controller.register_traffic(rule_list)
controller.start_traffic()
end = time.time()
print "Total %s" % (end-start)