from __future__ import print_function
import platform

if platform.system() != "Java":
    print("Load this file inside jython, if you need the stand-alone tool run: inql")
    exit(-1)

# JAVA GUI Import
from java.awt import Color, BorderLayout
from javax.swing import (JFrame, JPanel, JPopupMenu, JFileChooser)
from java.lang import System
from java.io import File

import os
import json
from inql.actions.executor import ExecutorAction
from inql.actions.flag import FlagAction
from inql.actions.browser import BrowserAction
from inql.introspection import init
from inql.constants import *
from inql.widgets.omnibar import Omnibar
from inql.widgets.fileview import FileView
from inql.utils import inheritsPopupMenu


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class GraphQLPanel():
    def __init__(self, actions=[], restore=None):
        self.actions = actions
        self.action_loadplaceholder = FlagAction(
            text_true="Disable Load placeholders",
            text_false="Enable Load placeholders")
        self.actions.append(self.action_loadplaceholder)
        self.action_generate_html = FlagAction(
            text_true="Disable HTML DOC Generation",
            text_false="Enable HTML DOC Generation",
            enabled=False)
        self.actions.append(self.action_generate_html)
        self.action_generate_schema = FlagAction(
            text_true="Disable Schema DOC Generation",
            text_false="Enable Schema DOC Generation",
            enabled=False)
        self.actions.append(self.action_generate_schema)
        self.action_generate_queries = FlagAction(
            text_true="Disable STUB Queries Generation",
            text_false="Enable STUB Queries Generation")
        self.actions.append(self.action_generate_queries)
        self.actions.append(BrowserAction())
        self.actions.append(ExecutorAction("Load", self.loadurl))
        self.actions = [a for a in reversed(self.actions)]

        self.this = JPanel()
        self.this.setLayout(BorderLayout())
        self.omnibar = Omnibar(
            hint=DEFAULT_LOAD_URL,
            label="Load",
            action=self.loadurl)
        self.this.add(BorderLayout.PAGE_START, self.omnibar.this)
        self.fileview = FileView(
            dir=os.getcwd(),
            filetree_label="Queries, Mutations and Subscriptions",
            payloadview_label="Query Template")
        self.this.add(BorderLayout.CENTER, self.fileview.this)
        self.fileview.addTreeListener(self.treeListener)
        self.fileview.addPayloadListener(self.payloadListener)

        self.popup = JPopupMenu()
        self.this.setComponentPopupMenu(self.popup)
        inheritsPopupMenu(self.this)

        for action in self.actions:
            self.popup.add(action.menuitem)

        self._state = []
        if restore:
            for target, load_placeholer, generate_html, generate_schema, generate_queries, flag in json.loads(restore):
                run(self, target, load_placeholer, generate_html, generate_schema, generate_queries, flag)

    def state(self):
        return json.dumps(self._state)

    def treeListener(self, e):
        try:
            host = [str(p) for p in e.getPath().getPath()][1]
            self._host = host
            fname = os.path.join(*[str(p) for p in e.getPath().getPath()][1:])
            self._fname = fname
            f = open(fname, "r")
            payload = f.read()
            for action in self.actions:
                action.ctx(host=host, payload=payload, fname=fname)
        except IOError:
            pass

    def payloadListener(self, e):
        try:
            doc = e.getDocument()
            payload = {
                "query": doc.getText(0, doc.getLength())
            }
            for action in self.actions:
                action.ctx(host=self._host, payload=json.dumps(payload), fname=self._fname)
        except Exception:
            pass

    def filepicker(self):
        fileChooser = JFileChooser()
        fileChooser.setCurrentDirectory(File(System.getProperty("user.home")))
        result = fileChooser.showOpenDialog(self.this)
        isApproveOption = result == JFileChooser.APPROVE_OPTION
        if isApproveOption:
            selectedFile = fileChooser.getSelectedFile()
            self.omnibox.showingHint = False
            self.url.setText(selectedFile.getAbsolutePath())
        return isApproveOption

    def loadurl(self, evt):
        target = self.omnibar.getText().strip()
        if target == DEFAULT_LOAD_URL:
            if self.filepicker():
                self.loadurl(evt)
        elif target.startswith('http://') or target.startswith('https://'):
            print("Quering GraphQL schema from: %s" % target)
            run(self, target, self.action_loadplaceholder.enabled,
                self.action_generate_html.enabled,
                self.action_generate_schema.enabled,
                self.action_generate_queries.enabled,
                "URL")
        elif not os.path.isfile(target):
            if self.filepicker():
                self.loadurl(evt)
        else:
            print("Loading JSON schema from: %s" % target)
            run(self, target,
                self.action_loadplaceholder.enabled,
                self.action_generate_html.enabled,
                self.action_generate_schema.enabled,
                self.action_generate_queries.enabled,
                "JSON")


def run(self, target, load_placeholer, generate_html, generate_schema, generate_queries, flag):
    self._state.append((target, load_placeholer, generate_html, generate_schema, generate_queries, flag))
    self.omnibar.reset()
    args = {"key": None, "proxy": None, "target": None, 'headers': [],
            "generate_html": generate_html, "generage_schema": generate_schema,
            "generate_queries": generate_queries, "detect": load_placeholer}
    if flag == "JSON":
        args["schema_json_file"] = target
    else:
        args["target"] = target

    args["detect"] = load_placeholer

    # call init method from Introspection tool
    init(AttrDict(args.copy()))
    self.fileview.filetree.refresh()
    return

if __name__ == "__main__":
    import tempfile
    tmpdir = tempfile.mkdtemp()
    from java.awt.event import ActionListener
    from javax.swing import JMenuItem

    class TestAction(ActionListener):
        def __init__(self, text):
            self.requests = {}
            self.menuitem = JMenuItem(text)
            self.menuitem.addActionListener(self)
            self.enabled = True
            self.menuitem.setEnabled(self.enabled)

        def actionPerformed(self, e):
            self.enabled = not self.enabled
            self.menuitem.setEnabled(self.enabled)

        def ctx(self, host=None, payload=None, fname=None):
            pass
    print("Changing dir to %s" % tmpdir)
    os.chdir(tmpdir)
    frame = JFrame("Burp TAB Tester")
    frame.setForeground(Color.black)
    frame.setBackground(Color.lightGray)
    cp = frame.getContentPane()
    cp.add(GraphQLPanel(actions=[TestAction("test it")]).this)
    frame.pack()
    frame.setVisible(True)
    frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE)
    from threading import Event
    Event().wait()
