"""Generate the bounded public browsing JMeter plan."""
from pathlib import Path
import xml.etree.ElementTree as E


def prop(node, name, value, kind="stringProp"):
    E.SubElement(node, kind, name=name).text = str(value)


root = E.Element("jmeterTestPlan", version="1.2", properties="5.0", jmeter="5.6.3")
tree = E.SubElement(root, "hashTree")
E.SubElement(tree, "TestPlan", guiclass="TestPlanGui", testclass="TestPlan", testname="AlumnixHub", enabled="true")
pt = E.SubElement(tree, "hashTree")
group = E.SubElement(pt, "ThreadGroup", guiclass="ThreadGroupGui", testclass="ThreadGroup", testname="Five visitors", enabled="true")
prop(group, "ThreadGroup.on_sample_error", "continue")
loop = E.SubElement(group, "elementProp", name="ThreadGroup.main_controller", elementType="LoopController")
prop(loop, "LoopController.loops", "5")
prop(loop, "LoopController.continue_forever", "false", "boolProp")
prop(group, "ThreadGroup.num_threads", "5")
prop(group, "ThreadGroup.ramp_time", "10")
gt = E.SubElement(pt, "hashTree")
timer = E.SubElement(gt, "ConstantTimer", guiclass="ConstantTimerGui", testclass="ConstantTimer", testname="Think time", enabled="true")
prop(timer, "ConstantTimer.delay", "1000")
E.SubElement(gt, "hashTree")
for route in ("/", "/events", "/news", "/alumni", "/mentors", "/surveys"):
    s = E.SubElement(gt, "HTTPSamplerProxy", guiclass="HttpTestSampleGui", testclass="HTTPSamplerProxy", testname=route, enabled="true")
    for name, value in {
        "domain": "${__P(host,77.47.192.6)}", "port": "${__P(port,4063)}",
        "protocol": "http", "path": route, "method": "GET",
        "connect_timeout": "5000", "response_timeout": "15000",
    }.items():
        prop(s, "HTTPSampler." + name, value)
    prop(s, "HTTPSampler.follow_redirects", "false", "boolProp")
    prop(s, "HTTPSampler.use_keepalive", "true", "boolProp")
    st = E.SubElement(gt, "hashTree")
    a = E.SubElement(st, "ResponseAssertion", guiclass="AssertionGui", testclass="ResponseAssertion", testname="HTTP 200", enabled="true")
    patterns = E.SubElement(a, "collectionProp", name="Asserion.test_strings")
    prop(patterns, "0", "200")
    prop(a, "Assertion.test_field", "Assertion.response_code")
    prop(a, "Assertion.test_type", "8", "intProp")
    E.SubElement(st, "hashTree")
target = Path(__file__).resolve().parents[1] / "tests/performance/public-browsing.jmx"
target.parent.mkdir(parents=True, exist_ok=True)
E.indent(root)
E.ElementTree(root).write(target, encoding="utf-8", xml_declaration=True)
print(target)
