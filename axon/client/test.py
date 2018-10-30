import time

from axon.client.traffic_elements import TrafficRule, \
    Endpoint, Port, Protocol, Action, Connected
from axon.client.cloud_traffic_controller import CloudTrafficController


rule_list = list()
rule_list.append(
    TrafficRule(Endpoint('15.27.10.161'), Endpoint('15.27.10.244'),
                Port(12345), Protocol.TCP, Connected.CONNECTED,
                Action.ALLOW)
)

rule_list.append(
    TrafficRule(Endpoint('15.27.10.244'), Endpoint('15.27.10.161'),
                Port(12345), Protocol.TCP, Connected.CONNECTED,
                Action.ALLOW)
)

start = time.time()
print rule_list
controller = CloudTrafficController(gateway_host='10.59.84.202')
controller.register_traffic(rule_list)
controller.stop_traffic()
controller.start_traffic()
controller.restart_traffic()

end = time.time()
print "Total %s" % (end - start)
