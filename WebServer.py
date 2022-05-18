# slicer imports
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

import socket


try:
    import urlparse
except ImportError:
    import urllib


    class urlparse(object):
        urlparse = urllib.parse.urlparse
        parse_qs = urllib.parse.parse_qs
#import uuid

# vtk imports
#import vtk.util.numpy_support

# WebServer imports
import glTFLib
#import dicomserver

#######################
from requesthandlers import *
#######################

#
# WebServer
#

class WebServer:
    def __init__(self, parent):
        parent.title = "Web Server"
        parent.categories = ["Servers"]
        parent.dependencies = []
        parent.contributors = ["Steve Pieper (Isomics)"]
        parent.helpText = """Provides an embedded web server for slicer that provides a web services API for interacting with slicer.
    """
        parent.acknowledgementText = """
This work was partially funded by NIH grant 3P41RR013218.
"""
        self.parent = parent


#
# WebServer widget
#

class WebServerWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        self.guiMessages = True
        self.consoleMessages = True

    def enter(self):
        pass

    def exit(self):
        self.logic.stop()

    def setLogging(self):
        self.consoleMessages = self.logToConsole.checked
        self.guiMessages = self.logToGUI.checked

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        self.logic = WebServerLogic(logMessage=self.logMessage)

        #start button
        self.startServerButton = qt.QPushButton("Start Server")
        self.startServerButton.toolTip = "Start web server with the selected options."
        self.layout.addWidget(self.startServerButton)
        self.startServerButton.connect('clicked()', self.logic.start)

        #stop button
        self.stopServerButton = qt.QPushButton("Stop Server")
        self.stopServerButton.toolTip = "Stop web server"
        self.layout.addWidget(self.stopServerButton)
        self.stopServerButton.connect('clicked()', self.logic.stop)

        # open browser page
        self.localConnectionButton = qt.QPushButton("Open static page in external browser")
        self.localConnectionButton.toolTip = "Open a connection to the server on the local machine with your system browser."
        self.layout.addWidget(self.localConnectionButton)
        self.localConnectionButton.connect('clicked()', self.openLocalConnection)

        # open slicer widget
        self.localQtConnectionButton = qt.QPushButton("Open static page in internal browser")
        self.localQtConnectionButton.toolTip = "Open a connection with Qt to the server on the local machine."
        self.layout.addWidget(self.localQtConnectionButton)
        self.localQtConnectionButton.connect('clicked()', lambda: self.openQtLocalConnection('http://localhost:2016'))

        # reload button - needs work
        self.reloadButton = qt.QPushButton("Reload")
        self.reloadButton.name = "WebServer Reload"
        self.reloadButton.toolTip = "Reload this module."
        self.layout.addWidget(self.reloadButton)
        self.reloadButton.connect('clicked(bool)', self.onReload)

        self.log = qt.QTextEdit()
        self.log.readOnly = True
        self.layout.addWidget(self.log)
        self.logMessage('<p>Status: <i>Idle</i>\n')

        # log to console
        self.logToConsole = qt.QCheckBox('Log to Console')
        self.logToConsole.setChecked(self.consoleMessages)
        self.logToConsole.toolTip = "Copy log messages to the python console and parent terminal"
        self.layout.addWidget(self.logToConsole)
        self.logToConsole.connect('clicked()', self.setLogging)

        # log to GUI
        self.logToGUI = qt.QCheckBox('Log to GUI')
        self.logToGUI.setChecked(self.guiMessages)
        self.logToGUI.toolTip = "Copy log messages to the log widget"
        self.layout.addWidget(self.logToGUI)
        self.logToGUI.connect('clicked()', self.setLogging)

        # clear log button
        self.clearLogButton = qt.QPushButton("Clear Log")
        self.clearLogButton.toolTip = "Clear the log window."
        self.layout.addWidget(self.clearLogButton)
        self.clearLogButton.connect('clicked()', self.log.clear)


        self.advancedCollapsibleButton = ctk.ctkCollapsibleButton()
        self.advancedCollapsibleButton.text = "Advanced"
        self.layout.addWidget(self.advancedCollapsibleButton)
        advancedFormLayout = qt.QFormLayout(self.advancedCollapsibleButton)
        self.advancedCollapsibleButton.collapsed = True

        # handlers

        self.enableSlicerHandler = qt.QCheckBox()
        self.enableSlicerHandler.toolTip = "Enable remote control of Slicer application (stop server to change option)"
        advancedFormLayout.addRow('Slicer API: ', self.enableSlicerHandler)

        self.enableSlicerHandlerExec = qt.QCheckBox()
        self.enableSlicerHandlerExec.toolTip = "Enable execution of arbitrary Python command using Slicer API. It only has effect if Slicer API is enabled, too (stop server to change option)."
        advancedFormLayout.addRow('Slicer API exec: ', self.enableSlicerHandlerExec)

        self.enableDICOMHandler = qt.QCheckBox()
        self.enableDICOMHandler.toolTip = "Enable serving Slicer DICOM database content via DICOMweb (stop server to change option)"
        advancedFormLayout.addRow('DICOMweb API: ', self.enableDICOMHandler)

        self.enableStaticPagesHandler = qt.QCheckBox()
        self.enableStaticPagesHandler.toolTip = "Enable serving static pages (stop server to change option)"
        advancedFormLayout.addRow('Static pages: ', self.enableStaticPagesHandler)


        
        # TODO: warning dialog on first connect
        # TODO: config option for port



        # export scene
        #self.exportSceneButton = qt.QPushButton("Export Scene")
        #self.exportSceneButton.toolTip = "Export the current scene to a web site (only models and tracts supported)."
        #self.layout.addWidget(self.exportSceneButton)
        #self.exportSceneButton.connect('clicked()', self.exportScene)

        # slivr button
        #self.slivrButton = qt.QPushButton("Open Slivr Demo")
        #self.slivrButton.toolTip = "Open the Slivr demo.  Example of VR export."
        #self.layout.addWidget(self.slivrButton)
        #self.slivrButton.connect('clicked()', self.openSlivrDemo)

        # ohif button
        #self.ohifButton = qt.QPushButton("Open OHIF Demo")
        #self.ohifButton.toolTip = "Open the OHIF demo.  Example of dicomweb access."
        #self.layout.addWidget(self.ohifButton)
        #self.ohifButton.connect('clicked()', self.openOHIFDemo)

        # Add spacer to layout
        self.layout.addStretch(1)

    def openLocalConnection(self):
        qt.QDesktopServices.openUrl(qt.QUrl('http://localhost:2016'))

    def openQtLocalConnection(self, url='http://localhost:2016'):
        self.webWidget = slicer.qSlicerWebWidget()
        html = """
    <h1>Loading from <a href="%(url)s">%(url)s/a></h1>
    """ % {'url': url}
        # self.webWidget.html = html
        self.webWidget.url = 'http://localhost:2016/work'
        self.webWidget.url = url
        self.webWidget.show()

    def openQIICRChartDemo(self):
        self.qiicrWebWidget = slicer.qSlicerWebWidget()
        self.qiicrWebWidget.setGeometry(50, 50, 1750, 1200)
        url = "http://pieper.github.io/qiicr-chart/dcsr/qiicr-chart"
        html = """
    <h1>Loading from <a href="%(url)s">%(url)s/a></h1>
    """ % {'url': url}
        # self.qiicrWebWidget.html = html
        self.qiicrWebWidget.url = url
        self.qiicrWebWidget.show()

    def exportScene(self):
        exportDirectory = ctk.ctkFileDialog.getExistingDirectory()
        if exportDirectory.endswith('/untitled'):
            # this happens when you select inside of a directory on mac
            exportDirectory = exportDirectory[:-len('/untitled')]
        if exportDirectory != '':
            self.logic.exportScene(exportDirectory)

    def openSlivrDemo(self):
        qt.QDesktopServices.openUrl(qt.QUrl('http://localhost:2016/slivr'))

    def openOHIFDemo(self):
        qt.QDesktopServices.openUrl(qt.QUrl('http://localhost:2016/ohif'))

    def onReload(self):
        self.logic.stop()
        ScriptedLoadableModuleWidget.onReload(self)
        slicer.modules.WebServerWidget.logic.start()

    def logMessage(self, *args):
        if self.consoleMessages:
            for arg in args:
                print(arg)
        if self.guiMessages:
            if len(self.log.html) > 1024 * 256:
                self.log.clear()
                self.log.insertHtml("Log cleared\n")
            for arg in args:
                self.log.insertHtml(arg)
            self.log.insertPlainText('\n')
            self.log.ensureCursorVisible()
            self.log.repaint()
            # slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)

    def cleanup(self):
        # TODO this never gets called when slicer is Xed out for some reason (even tho i thought that's the whole point of this method...), so the server keeps running forever
        self.logic.stop()
        super().cleanup()




#
# WebServer logic
#

class WebServerLogic:
    """Include a concrete subclass of SimpleHTTPServer
    that speaks slicer.
    """

    def __init__(self, logMessage=None):
        if logMessage:
            self.logMessage = logMessage
        self.port = 2016
        self.server = None
        self.logFile = '/tmp/WebServerLogic.log'

        moduleDirectory = os.path.dirname(slicer.modules.webserver.path.encode())
        self.docroot = moduleDirectory + b"/docroot"

    def findFreePort(self, port=2016):
        """returns a port that is not apparently in use"""
        portFree = False
        while not portFree:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("", port))
            except socket.error as e:
                portFree = False
                port += 1
            finally:
                s.close()
                portFree = True
        return port


    def getSceneBounds(self):
        # scene bounds
        sceneBounds = None
        for node in slicer.util.getNodes('*').values():
            if node.IsA('vtkMRMLDisplayableNode'):
                bounds = [0, ] * 6
                if sceneBounds is None:
                    sceneBounds = bounds
                node.GetRASBounds(bounds)
                for element in range(0, 6):
                    op = (min, max)[element % 2]
                    sceneBounds[element] = op(sceneBounds[element], bounds[element])
        return sceneBounds

    def exportScene(self, exportDirectory):
        """Export a simple scene that can run independent of Slicer.

        This exports the data in a standard format with the idea that other
        sites can be built externally to make the data more usable."""

        scale = 15
        sceneBounds = self.getSceneBounds()
        center = [0.5 * (sceneBounds[0] + sceneBounds[1]), 0.5 * (sceneBounds[2] + sceneBounds[3]),
                  0.5 * (sceneBounds[4] + sceneBounds[5])]
        target = [scale * center[0] / 1000., scale * center[1] / 1000., scale * center[2] / 1000.]

        cameraPosition = [target[1], target[2], target[0] + 2]

        html = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <script src="https://aframe.io/releases/0.6.1/aframe.min.js"></script>
    <script src="https://cdn.rawgit.com/tizzle/aframe-orbit-controls-component/v0.1.12/dist/aframe-orbit-controls-component.min.js"></script>
    <style type="text/css">
      * {font-family: sans-serif;}
    </style>
  </head>
  <body>

    <a-scene >
      <a-entity
          id="camera"
          camera="fov: 80; zoom: 1;"
          position="%CAMERA_POSITION%"
          orbit-controls="
              autoRotate: false;
              target: #target;
              enableDamping: true;
              dampingFactor: 0.125;
              rotateSpeed:0.25;
              minDistance:1;
              maxDistance:100;
              "
          >
      </a-entity>

      <a-entity id="target" position="%TARGET_POSITION%"></a-entity>
      <a-entity id="mrml" position="0 0 0" scale="%SCALE%" rotation="-90 180 0">
        <a-gltf-model src="./mrml.gltf"></a-gltf-model>
      </a-entity>
    </a-scene>

  </body>
</html>
"""
        html = html.replace("%CAMERA_POSITION%", "%g %g %g" % (cameraPosition[0], cameraPosition[1], cameraPosition[2]))
        html = html.replace("%SCALE%", "%g %g %g" % (scale, scale, scale))
        html = html.replace("%TARGET_POSITION%", "%g %g %g" % (target[1], target[2], target[0]))

        htmlPath = os.path.join(exportDirectory, "index.html")
        print('saving to', htmlPath)
        fp = open(htmlPath, "w")
        fp.write(html)
        fp.close()

        exporter = glTFLib.glTFExporter(slicer.mrmlScene)
        glTF = exporter.export(options={
            "fiberMode": "tubes",
        })
        glTFPath = os.path.join(exportDirectory, "mrml.gltf")
        print('saving to', glTFPath)
        fp = open(glTFPath, "w")
        fp.write(glTF)
        fp.close()

        for bufferFileName in exporter.buffers.keys():
            print('saving to', bufferFileName)
            fp = open(os.path.join(exportDirectory, bufferFileName), "wb")
            fp.write(exporter.buffers[bufferFileName].data)
            fp.close()

        print('done exporting')

    def logMessage(self, *args):
        for arg in args:
            print("Logic: " + arg)

    def start(self):
        from slicerserver import Server
        """Set up the server"""
        self.stop()
        self.port = WebServerLogic.findFreePort(self.port)
        self.logMessage("Starting server on port %d" % self.port)
        self.logMessage('docroot: %s' % self.docroot)
        # for testing webxr
        # e.g. certfile = '/Users/pieper/slicer/latest/SlicerWeb/localhost.pem'
        # openssl req -new -x509 -keyout localhost.pem -out localhost.pem -days 365 -nodes
        # TODO maybe add a field to the widget where the user puts the path to their cert/key files, for now put them in the auth directory
        authpath = os.path.dirname(slicer.modules.webserver.path.encode()) + b"/auth"
        
        ## TODO if keys are present run sercure, if not dont run
        try:
            t = open(authpath + b"/cert.pem")
            t = open(authpath + b"/key.pem")
            certfile = authpath + b"/cert.pem"
            keyfile = authpath + b"/key.pem"
            t = None
            
        except FileNotFoundError:
            print("No Certificate/Key found, server will run in insecure mode")
            certfile = None
            keyfile = None
        except:
            print("Unknown error, server will run in insecure mode")
            certfile = None
            keyfile = None
        #self.server = SlicerHTTPServer(docroot=self.docroot, server_address=("", self.port), logFile=self.logFile,
        #                               logMessage=self.logMessage, certfile=certfile, keyfile=keyfile)
        self.server = Server(docroot=self.docroot, server_address=("", self.port), logFile=self.logFile,
                                 logMessage=self.logMessage, certfile=certfile, keyfile=keyfile)
        self.server.start()
        #self.server.start()

    def stop(self):
        if self.server:
            self.server.stop()
