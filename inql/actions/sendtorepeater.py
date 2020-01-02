import platform

if platform.system() != "Java":
    print("Load this file inside jython, if you need the stand-alone tool run: inql")
    exit(-1)

from burp import IProxyListener, IContextMenuFactory
from java.awt.event import ActionListener
from javax.swing import JMenuItem
from inql.constants import *
from org.python.core.util import StringUtil
from inql.utils import stringjoin
import re


def override_headers(http_header, overrideheaders):
    ree = [(
        re.compile("^%s\s:\s*[^\n]+$" % re.escape(header)),
        re.compile("%s: %s" % (re.escape(header), re.escape(val))))
        for (header, val) in overrideheaders]
    h = http_header
    for find, replace in ree:
        h = re.sub(find, replace, h)

    return h


class RepeaterSender(IProxyListener, ActionListener, IContextMenuFactory):
    def __init__(self, callbacks, helpers, text, overrideheaders):
        self.requests = {}
        self.helpers = helpers
        self.callbacks = callbacks
        self.menuitem = JMenuItem(text)
        self.burp_menuitem = JMenuItem("inql: %s" % text)
        self.callbacks.registerProxyListener(self)
        self.menuitem.addActionListener(self)
        self.menuitem.setEnabled(False)
        self.burp_menuitem.addActionListener(self)
        self.burp_menuitem.setEnabled(False)
        self.index = 0
        self.host = None
        self.payload = None
        self.fname = None
        for r in self.callbacks.getProxyHistory():
            self.processRequest(self.helpers.analyzeRequest(r), r.getRequest())
        self.callbacks.registerContextMenuFactory(self)
        self.overrideheaders = overrideheaders

    def processProxyMessage(self, messageIsRequest, message):
        if messageIsRequest:
            self.processRequest(self.helpers.analyzeRequest(message.getMessageInfo()),
                                message.getMessageInfo().getRequest())

    def processRequest(self, reqinfo, reqbody):
        url = str(reqinfo.getUrl())
        if any([url.endswith(x) for x in URLS]):
            for h in reqinfo.getHeaders():
                if h.lower().startswith("host:"):
                    domain = h[5:].strip()

            method = reqinfo.getMethod()
            try:
                self.requests[domain]
            except KeyError:
                self.requests[domain] = {'POST': None, 'PUT': None, 'GET': None}
            self.requests[domain][method] = (reqinfo, reqbody)

    def actionPerformed(self, e):
        req = self.requests[self.host]['POST'] or self.requests[self.host]['PUT'] or self.requests[self.host]['GET']
        if req:
            info = req[0]
            body = req[1]
            headers = body[:info.getBodyOffset()].tostring()

            try:
                self.overrideheaders[self.host]
            except KeyError:
                self.overrideheaders[self.host] = {}

            repeater_body = StringUtil.toBytes(stringjoin(
                override_headers(headers, self.overrideheaders[self.host]),
                self.payload))

            self.callbacks.sendToRepeater(info.getUrl().getHost(), info.getUrl().getPort(),
                                          info.getUrl().getProtocol() == 'https', repeater_body,
                                          'GraphQL #%s' % self.index)
            self.index += 1

    def ctx(self, host=None, payload=None, fname=None):
        self.host = host
        self.payload = payload
        self.fname = fname

        if not self.fname.endswith('.query'):
            self.menuitem.setEnabled(False)
            self.burp_menuitem.setEnabled(False)
            return

        try:
            self.requests[host]
            self.menuitem.setEnabled(True)
            self.burp_menuitem.setEnabled(True)
        except KeyError:
            self.menuitem.setEnabled(False)
            self.burp_menuitem.setEnabled(False)

    def createMenuItems(self, invocation):
        try:
            r = invocation.getSelectedMessages()[0]
            info = self.helpers.analyzeRequest(r)
            url = str(info.getUrl())
            if not any([x in url for x in URLS]):
                return None
            body = r.getRequest()[info.getBodyOffset():].tostring()
            for h in info.getHeaders():
                if h.lower().startswith("host:"):
                    domain = h[5:].strip()

            self.ctx(fname='dummy.query', host=domain, payload=body)
            mymenu = []
            mymenu.append(self.burp_menuitem)
        except Exception as ex:
            return None
        return mymenu