import json
import sys
import time

import numpy
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

import glTFLib

try:
    import urlparse
except ImportError:
    import urllib


    class urlparse(object):
        urlparse = urllib.parse.urlparse
        parse_qs = urllib.parse.parse_qs


from typing import Union, Optional, Awaitable

from tornado.websocket import WebSocketHandler
#from requesthandlers import DICOMRequestHandler, SlicerRequestHandler, StaticRequestHandler
from requesthandlers import header_builder, DICOMRequestHandler

class SlicerWebSocketHandler(WebSocketHandler):
    def logMessage(self, message):
        print(message)
    
    def check_origin(self, origin):
        return True

    def open(self, *args: str, **kwargs: str) -> Optional[Awaitable[None]]:
        #self.slicerRequestHandler = SlicerRequestHandler()
        return super().open(*args, **kwargs)

    def on_close(self) -> None:
        super().on_close()

    def on_message(self, message: Union[str, bytes]) -> Optional[Awaitable[None]]:
        #print(message)
        header = self.parseHeader(message)
        print("Request header is", header)

        if header == "slicer":
            index = message.find("/")
            request = message[index:]
            index = message.find(" ")
            requestBody = "" if index == -1 else message[index:]
            contentType, responseBody = self.handleSlicerRequest(request, requestBody) 
            #print("writing to file?")
            #imgOut = open("img.png", 'wb')
            #imgOut.write(responseBody)
            if responseBody != None:
                self.write_message(responseBody, True)
            else:
                self.write_message("no response body")
        elif header == "dicom":
            index = message.find(" ")
            message = message.encode()
            if index == -1:
                requestBody = ""
                request = urlparse.urlparse(message)
            else:
                requestBody = message[index:]
                request = urlparse.urlparse(message[:index])
                #request = request.decode()
            contentType, responseBody = DICOMRequestHandler.handleDICOMRequest(request, requestBody, self)
            if responseBody != None:
                self.write_message(responseBody, True)
            else:
                self.write_message("no response body")


    def parseHeader(self, message):
        splitMessage = message.split("/")
        return splitMessage[0]

##################################
# slice request handler copy paste
##################################
    

    def registerOneTimeBuffers(self, buffers):
        """ This allows data to be made avalable for subsequent access
        at a specific endpoint by filename.  To avoid memory buildup
        they are only accessible once and then deleted.

        The specific use case is for binary files containing glTF array
        data that is referenced from the glTF json.
        """
        # TODO: this should not be stored in the widget, but that is a known place where it
        # can persist across the lifetime of the server
        slicer.modules.WebServerWidget.oneTimeBuffers = buffers

    def vtkImageDataToPNG(self, imageData):
        """Return a buffer of png data using the data
        from the vtkImageData.
        """
        writer = vtk.vtkPNGWriter()
        writer.SetWriteToMemory(True)
        writer.SetInputData(imageData)
        # use compression 0 since data transfer is faster than compressing
        writer.SetCompressionLevel(0)
        writer.Write()
        result = writer.GetResult()
        if result is not None:
            pngArray = vtk.util.numpy_support.vtk_to_numpy(result)
            pngData = pngArray.tobytes()
        else:
            pngData = None
        return pngData

    def handleSlicerRequest(self, request, requestBody):
        print("request is", request)
        #print(requestBody)
        responseBody = None
        contentType = b'text/plain'
        try:
            #if hasattr(slicer.modules.WebServerWidget, 'oneTimeBuffers'):
            #    self.oneTimeBuffers = slicer.modules.WebServerWidget.oneTimeBuffers
            #else:
            #    if not hasattr(self, 'oneTimeBuffers'):
            #        self.oneTimeBuffers = {}
            #bufferFileName = request[1:].decode()  # strip first, make string
            #bufferFileName = request
            #if bufferFileName in self.oneTimeBuffers.keys():
            #    contentType = b'application/octet-stream'
            #    responseBody = self.oneTimeBuffers[bufferFileName].tobytes()
            #    del (self.oneTimeBuffers[bufferFileName])
            if request.find('/repl') == 0:
                responseBody = self.repl(request, requestBody)
            elif request.find('/preset') == 0:
                responseBody = self.preset(request)
            elif request.find('/timeimage') == 0:
                responseBody = self.timeimage(request.encode())
                contentType = b'image/png'
            elif request.find('/slice') == 0:
                responseBody = self.slice(request)
                contentType = b'image/png'
            elif request.find('/threeD') == 0:
                responseBody = self.threeD(request)
                contentType = b'image/png'
            elif request.find('/mrml') == 0:
                responseBody = self.mrml(request)
                contentType = b'application/json'
            elif request.find('/tracking') == 0:
                responseBody = self.tracking(request)
            elif request.find('/eulers') == 0:
                responseBody = self.eulers(request)
            elif request.find('/volumeSelection') == 0:
                responseBody = self.volumeSelection(request)
            elif request.find('/volumes') == 0:
                responseBody = self.volumes(request, requestBody)
                contentType = b'application/json'
            elif request.find('/volume') == 0:
                responseBody = self.volume(request, requestBody)
                contentType = b'application/octet-stream'
            elif request.find('/gridTransforms') == 0:
                responseBody = self.gridTransforms(request, requestBody)
                contentType = b'application/json',
            elif request.find('/gridTransform') == 0:
                responseBody = self.gridTransform(request, requestBody)
                print("responseBody", len(responseBody))
                contentType = b'application/octet-stream'
            elif request.find('/fiducials') == 0:
                responseBody = self.fiducials(request, requestBody)
                contentType = b'application/json'
            elif request.find('/fiducial') == 0:
                responseBody = self.fiducial(request, requestBody)
                contentType = b'application/json'
            elif request.find('/accessStudy') == 0:
                responseBody = self.accessStudy(request, requestBody)
                contentType = b'application/json'
            else:
                responseBody = b"unknown command \"" + request + b"\""
        except:
            self.logMessage("Could not handle slicer command: %s" % request)
            etype, value, tb = sys.exc_info()
            import traceback
            #self.logMessage(etype, value)
            self.logMessage(traceback.format_tb(tb))
            print(etype, value)
            print(traceback.format_tb(tb))
            for frame in traceback.format_tb(tb):
                print(frame)
        return contentType, responseBody

    def repl(self, request, requestBody):
        """example:
    curl -X POST localhost:2016/slicer/repl --data "slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)"
        """
        self.logMessage('repl with body %s' % requestBody)
        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)
        if requestBody:
            source = requestBody
        else:
            try:
                source = urllib.parse.unquote(q['source'][0])
            except KeyError:
                self.logMessage('need to supply source code to run')
                return ""
        self.logMessage('will run %s' % source)
        exec("__replResult = {}", globals())
        exec(source, globals())
        result = json.dumps(eval("__replResult", globals())).encode()
        self.logMessage('result: %s' % result)
        return result

    def preset(self, request):
        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)
        try:
            id = q['id'][0].strip().lower()
        except KeyError:
            id = 'default'

        if id == 'compareview':
            #
            # first, get the sample data
            #
            if not slicer.util.getNodes('MRBrainTumor*'):
                import SampleData
                sampleDataLogic = SampleData.SampleDataLogic()
                tumor1 = sampleDataLogic.downloadMRBrainTumor1()
                tumor2 = sampleDataLogic.downloadMRBrainTumor2()
            else:
                tumor1 = slicer.util.getNode('MRBrainTumor1')
                tumor2 = slicer.util.getNode('MRBrainTumor2')
            # set up the display in the default configuration
            layoutManager = slicer.app.layoutManager()
            redComposite = layoutManager.sliceWidget('Red').mrmlSliceCompositeNode()
            yellowComposite = layoutManager.sliceWidget('Yellow').mrmlSliceCompositeNode()
            redComposite.SetBackgroundVolumeID(tumor1.GetID())
            yellowComposite.SetBackgroundVolumeID(tumor2.GetID())
            yellowSlice = layoutManager.sliceWidget('Yellow').mrmlSliceNode()
            yellowSlice.SetOrientationToAxial()
            redSlice = layoutManager.sliceWidget('Red').mrmlSliceNode()
            redSlice.SetOrientationToAxial()
            tumor1Display = tumor1.GetDisplayNode()
            tumor2Display = tumor2.GetDisplayNode()
            tumor2Display.SetAutoWindowLevel(0)
            tumor2Display.SetWindow(tumor1Display.GetWindow())
            tumor2Display.SetLevel(tumor1Display.GetLevel())
            applicationLogic = slicer.app.applicationLogic()
            applicationLogic.FitSliceToAll()
            return (json.dumps([tumor1.GetName(), tumor2.GetName()]).encode())
        if id == 'amigo-2012-07-02':
            #
            # first, get the data
            #
            if not slicer.util.getNodes('ID_1'):
                tumor1 = slicer.util.loadVolume('/Users/pieper/data/2July2012/bl-data1/ID_1.nrrd')
                tumor2 = slicer.util.loadVolume('/Users/pieper/data/2July2012/bl-data2/ID_6.nrrd')
            else:
                tumor1 = slicer.util.getNode('ID_1')
                tumor2 = slicer.util.getNode('ID_6')
            # set up the display in the default configuration
            layoutManager = slicer.app.layoutManager()
            redComposite = layoutManager.sliceWidget('Red').mrmlSliceCompositeNode()
            yellowComposite = layoutManager.sliceWidget('Yellow').mrmlSliceCompositeNode()
            yellowSlice = layoutManager.sliceWidget('Yellow').mrmlSliceNode()
            yellowSlice.SetOrientationToAxial()
            redSlice = layoutManager.sliceWidget('Red').mrmlSliceNode()
            redSlice.SetOrientationToAxial()
            redComposite.SetBackgroundVolumeID(tumor1.GetID())
            yellowComposite.SetBackgroundVolumeID(tumor2.GetID())
            applicationLogic.FitSliceToAll()
            return (json.dumps([tumor1.GetName(), tumor2.GetName()]).encode())
        elif id == 'default':
            #
            # first, get the sample data
            #
            if not slicer.util.getNodes('MR-head*'):
                import SampleData
                sampleDataLogic = SampleData.SampleDataLogic()
                head = sampleDataLogic.downloadMRHead()
                return (json.dumps([head.GetName(), ]).encode())

        return ("no matching preset")

    def setupMRMLTracking(self):
        if not hasattr(self, "trackingDevice"):
            """ set up the mrml parts or use existing """
            nodes = slicer.mrmlScene.GetNodesByName('trackingDevice')
            if nodes.GetNumberOfItems() > 0:
                self.trackingDevice = nodes.GetItemAsObject(0)
                nodes = slicer.mrmlScene.GetNodesByName('tracker')
                self.tracker = nodes.GetItemAsObject(0)
            else:
                # trackingDevice cursor
                self.cube = vtk.vtkCubeSource()
                self.cube.SetXLength(30)
                self.cube.SetYLength(70)
                self.cube.SetZLength(5)
                self.cube.Update()
                # display node
                self.modelDisplay = slicer.vtkMRMLModelDisplayNode()
                self.modelDisplay.SetColor(1, 1, 0)  # yellow
                slicer.mrmlScene.AddNode(self.modelDisplay)
                # self.modelDisplay.SetPolyData(self.cube.GetOutputPort())
                # Create model node
                self.trackingDevice = slicer.vtkMRMLModelNode()
                self.trackingDevice.SetScene(slicer.mrmlScene)
                self.trackingDevice.SetName("trackingDevice")
                self.trackingDevice.SetAndObservePolyData(self.cube.GetOutputDataObject(0))
                self.trackingDevice.SetAndObserveDisplayNodeID(self.modelDisplay.GetID())
                slicer.mrmlScene.AddNode(self.trackingDevice)
                # tracker
                self.tracker = slicer.vtkMRMLLinearTransformNode()
                self.tracker.SetName('tracker')
                slicer.mrmlScene.AddNode(self.tracker)
                self.trackingDevice.SetAndObserveTransformNodeID(self.tracker.GetID())

    def eulers(self, request):
        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)
        self.logMessage(q)
        alpha, beta, gamma = list(map(float, q['angles'][0].split(',')))

        self.setupMRMLTracking()
        transform = vtk.vtkTransform()
        transform.RotateZ(alpha)
        transform.RotateX(beta)
        transform.RotateY(gamma)
        self.tracker.SetMatrixTransformToParent(transform.GetMatrix())

        return (b"got it")

    def tracking(self, request):
        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)
        self.logMessage(q)
        try:
            transformMatrix = list(map(float, q['m'][0].split(',')))
        except KeyError:
            transformMatrix = None
        try:
            quaternion = list(map(float, q['q'][0].split(',')))
        except KeyError:
            quaternion = None
        try:
            position = list(map(float, q['p'][0].split(',')))
        except KeyError:
            position = None

        self.setupMRMLTracking()
        m = vtk.vtkMatrix4x4()
        self.tracker.GetMatrixTransformToParent(m)

        if transformMatrix:
            for row in range(3):
                for column in range(3):
                    m.SetElement(row, column, transformMatrix[3 * row + column])
                    m.SetElement(row, column, transformMatrix[3 * row + column])
                    m.SetElement(row, column, transformMatrix[3 * row + column])
                    # m.SetElement(row,column, transformMatrix[3*row+column])

        if position:
            for row in range(3):
                m.SetElement(row, 3, position[row])

        if quaternion:
            qu = vtk.vtkQuaternion['float64']()
            qu.SetW(quaternion[0])
            qu.SetX(quaternion[1])
            qu.SetY(quaternion[2])
            qu.SetZ(quaternion[3])
            m3 = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
            qu.ToMatrix3x3(m3)
            for row in range(3):
                for column in range(3):
                    m.SetElement(row, column, m3[row][column])

        self.tracker.SetMatrixTransformToParent(m)

        return (b"got it")

    def volumeSelection(self, request):
        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)
        try:
            cmd = q['cmd'][0].strip().lower()
        except KeyError:
            cmd = 'next'
        options = ['next', 'previous']
        if not cmd in options:
            cmd = 'next'

        applicationLogic = slicer.app.applicationLogic()
        selectionNode = applicationLogic.GetSelectionNode()
        currentNodeID = selectionNode.GetActiveVolumeID()
        currentIndex = 0
        if currentNodeID:
            nodes = slicer.util.getNodes('vtkMRML*VolumeNode*')
            for nodeName in nodes:
                if nodes[nodeName].GetID() == currentNodeID:
                    break
                currentIndex += 1
        if currentIndex >= len(nodes):
            currentIndex = 0
        if cmd == 'next':
            newIndex = currentIndex + 1
        elif cmd == 'previous':
            newIndex = currentIndex - 1
        if newIndex >= len(nodes):
            newIndex = 0
        if newIndex < 0:
            newIndex = len(nodes) - 1
        volumeNode = nodes[nodes.keys()[newIndex]]
        selectionNode.SetReferenceActiveVolumeID(volumeNode.GetID())
        applicationLogic.PropagateVolumeSelection(0)
        return (b"got it")

    def volumes(self, request, requestBody):
        volumes = []
        mrmlVolumes = slicer.util.getNodes('vtkMRMLScalarVolumeNode*')
        mrmlVolumes.update(slicer.util.getNodes('vtkMRMLLabelMapVolumeNode*'))
        for id_ in mrmlVolumes.keys():
            volumeNode = mrmlVolumes[id_]
            volumes.append({"name": volumeNode.GetName(), "id": volumeNode.GetID()})
        return (json.dumps(volumes).encode())

    def volume(self, request, requestBody):
        p = urlparse.urlparse(request.decode())
        q = urlparse.parse_qs(p.query)
        try:
            volumeID = q['id'][0].strip()
        except KeyError:
            volumeID = 'vtkMRMLScalarVolumeNode*'

        if requestBody:
            return self.postNRRD(volumeID, requestBody)
        else:
            return self.getNRRD(volumeID)

    def gridTransforms(self, request, requestBody):
        gridTransforms = []
        mrmlGridTransforms = slicer.util.getNodes('vtkMRMLGridTransformNode*')
        for id_ in mrmlGridTransforms.keys():
            gridTransform = mrmlGridTransforms[id_]
            gridTransforms.append({"name": gridTransform.GetName(), "id": gridTransform.GetID()})
        return (json.dumps(gridTransforms).encode())

    def gridTransform(self, request, requestBody):
        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)
        try:
            transformID = q['id'][0].strip()
        except KeyError:
            transformID = 'vtkMRMLGridTransformNode*'

        if requestBody:
            return self.postTransformNRRD(transformID, requestBody)
        else:
            return self.getTransformNRRD(transformID)

    def postNRRD(self, volumeID, requestBody):
        """Convert a binary blob of nrrd data into a node in the scene.
        Overwrite volumeID if it exists, otherwise create new"""

        if requestBody[:4] != b"NRRD":
            self.logMessage('Cannot load non-nrrd file (magic is %s)' % requestBody[:4])
            return

        fields = {}
        endOfHeader = requestBody.find(b'\n\n')  # TODO: could be \r\n
        header = requestBody[:endOfHeader]
        self.logMessage(header)
        for line in header.split(b'\n'):
            colonIndex = line.find(b':')
            if line[0] != '#' and colonIndex != -1:
                key = line[:colonIndex]
                value = line[colonIndex + 2:]
                fields[key] = value

        if fields[b'type'] != b'short':
            self.logMessage('Can only read short volumes')
            return b"{'status': 'failed'}"
        if fields[b'dimension'] != b'3':
            self.logMessage('Can only read 3D, 1 component volumes')
            return b"{'status': 'failed'}"
        if fields[b'endian'] != b'little':
            self.logMessage('Can only read little endian')
            return b"{'status': 'failed'}"
        if fields[b'encoding'] != b'raw':
            self.logMessage('Can only read raw encoding')
            return b"{'status': 'failed'}"
        if fields[b'space'] != b'left-posterior-superior':
            self.logMessage('Can only read space in LPS')
            return b"{'status': 'failed'}"

        imageData = vtk.vtkImageData()
        imageData.SetDimensions(list(map(int, fields[b'sizes'].split(b' '))))
        imageData.AllocateScalars(vtk.VTK_SHORT, 1)

        origin = list(map(float, fields[b'space origin'].replace(b'(', b'').replace(b')', b'').split(b',')))
        origin[0] *= -1
        origin[1] *= -1

        directions = []
        directionParts = fields[b'space directions'].split(b')')[:3]
        for directionPart in directionParts:
            part = directionPart.replace(b'(', b'').replace(b')', b'').split(b',')
            directions.append(list(map(float, part)))

        ijkToRAS = vtk.vtkMatrix4x4()
        ijkToRAS.Identity()
        for row in range(3):
            ijkToRAS.SetElement(row, 3, origin[row])
            for column in range(3):
                element = directions[column][row]
                if row < 2:
                    element *= -1
                ijkToRAS.SetElement(row, column, element)

        try:
            node = slicer.util.getNode(volumeID)
        except slicer.util.MRMLNodeNotFoundException:
            node = None
        if not node:
            node = slicer.vtkMRMLScalarVolumeNode()
            node.SetName(volumeID)
            slicer.mrmlScene.AddNode(node)
            node.CreateDefaultDisplayNodes()
        node.SetAndObserveImageData(imageData)
        node.SetIJKToRASMatrix(ijkToRAS)

        pixels = numpy.frombuffer(requestBody[endOfHeader + 2:], dtype=numpy.dtype('int16'))
        array = slicer.util.array(node.GetID())
        array[:] = pixels.reshape(array.shape)
        imageData.GetPointData().GetScalars().Modified()

        displayNode = node.GetDisplayNode()
        displayNode.ProcessMRMLEvents(displayNode, vtk.vtkCommand.ModifiedEvent, "")
        # TODO: this could be optional
        slicer.app.applicationLogic().GetSelectionNode().SetReferenceActiveVolumeID(node.GetID())
        slicer.app.applicationLogic().PropagateVolumeSelection()

        return b"{'status': 'success'}"

    def getNRRD(self, volumeID):
        """Return a nrrd binary blob with contents of the volume node"""
        volumeNode = slicer.util.getNode(volumeID)
        volumeArray = slicer.util.array(volumeID)

        if volumeNode is None or volumeArray is None:
            self.logMessage('Could not find requested volume')
            return None
        supportedNodes = ["vtkMRMLScalarVolumeNode", "vtkMRMLLabelMapVolumeNode"]
        if not volumeNode.GetClassName() in supportedNodes:
            self.logMessage('Can only get scalar volumes')
            return None

        imageData = volumeNode.GetImageData()

        supportedScalarTypes = ["short", "double"]
        scalarType = imageData.GetScalarTypeAsString()
        if scalarType not in supportedScalarTypes:
            self.logMessage('Can only get volumes of types %s, not %s' % (str(supportedScalarTypes), scalarType))
            self.logMessage('Converting to short, but may cause data loss.')
            volumeArray = numpy.array(volumeArray, dtype='int16')
            scalarType = 'short'

        sizes = imageData.GetDimensions()
        sizes = " ".join(list(map(str, sizes)))

        originList = [0, ] * 3
        directionLists = [[0, ] * 3, [0, ] * 3, [0, ] * 3]
        ijkToRAS = vtk.vtkMatrix4x4()
        volumeNode.GetIJKToRASMatrix(ijkToRAS)
        for row in range(3):
            originList[row] = ijkToRAS.GetElement(row, 3)
            for column in range(3):
                element = ijkToRAS.GetElement(row, column)
                if row < 2:
                    element *= -1
                directionLists[column][row] = element
        originList[0] *= -1
        originList[1] *= -1
        origin = '(' + ','.join(list(map(str, originList))) + ')'
        directions = ""
        for directionList in directionLists:
            direction = '(' + ','.join(list(map(str, directionList))) + ')'
            directions += direction + " "
        directions = directions[:-1]

        # should look like:
        # space directions: (0,1,0) (0,0,-1) (-1.2999954223632812,0,0)
        # space origin: (86.644897460937486,-133.92860412597656,116.78569793701172)

        nrrdHeader = """NRRD0004
# Complete NRRD file format specification at:
# http://teem.sourceforge.net/nrrd/format.html
type: %%scalarType%%
dimension: 3
space: left-posterior-superior
sizes: %%sizes%%
space directions: %%directions%%
kinds: domain domain domain
endian: little
encoding: raw
space origin: %%origin%%

""".replace("%%scalarType%%", scalarType).replace("%%sizes%%", sizes).replace("%%directions%%", directions).replace(
            "%%origin%%", origin)

        nrrdData = nrrdHeader.encode() + volumeArray.tobytes()
        return nrrdData

    def getTransformNRRD(self, transformID):
        """Return a nrrd binary blob with contents of the transform node"""
        transformNode = slicer.util.getNode(transformID)
        transformArray = slicer.util.array(transformID)

        if transformNode is None or transformArray is None:
            self.logMessage('Could not find requested transform')
            return None
        supportedNodes = ["vtkMRMLGridTransformNode", ]
        if not transformNode.GetClassName() in supportedNodes:
            self.logMessage('Can only get grid transforms')
            return None

        # map the vectors to be in the LPS measurement frame
        # (need to make a copy so as not to change the slicer transform)
        lpsArray = numpy.array(transformArray)
        lpsArray *= numpy.array([-1, -1, 1])

        imageData = transformNode.GetTransformFromParent().GetDisplacementGrid()

        # for now, only handle non-oriented grid transform as
        # generated from LandmarkRegistration
        # TODO: generalize for any GridTransform node
        # -- here we assume it is axial as generated by LandmarkTransform

        sizes = (3,) + imageData.GetDimensions()
        sizes = " ".join(list(map(str, sizes)))

        spacing = list(imageData.GetSpacing())
        spacing[0] *= -1  # RAS to LPS
        spacing[1] *= -1  # RAS to LPS
        directions = '(%g,0,0) (0,%g,0) (0,0,%g)' % tuple(spacing)

        origin = list(imageData.GetOrigin())
        origin[0] *= -1  # RAS to LPS
        origin[1] *= -1  # RAS to LPS
        origin = '(%g,%g,%g)' % tuple(origin)

        # should look like:
        # space directions: (0,1,0) (0,0,-1) (-1.2999954223632812,0,0)
        # space origin: (86.644897460937486,-133.92860412597656,116.78569793701172)

        nrrdHeader = """NRRD0004
# Complete NRRD file format specification at:
# http://teem.sourceforge.net/nrrd/format.html
type: float
dimension: 4
space: left-posterior-superior
sizes: %%sizes%%
space directions: %%directions%%
kinds: vector domain domain domain
endian: little
encoding: raw
space origin: %%origin%%

""".replace("%%sizes%%", sizes).replace("%%directions%%", directions).replace("%%origin%%", origin)

        nrrdData = nrrdHeader.encode() + lpsArray.tobytes()
        return nrrdData

    def fiducials(self, request, requestBody):
        """return fiducials list in ad hoc json structure"""
        fiducials = {}
        for markupsNode in slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode'):
            displayNode = markupsNode.GetDisplayNode()
            node = {}
            node['name'] = markupsNode.GetName()
            node['color'] = displayNode.GetSelectedColor()
            node['scale'] = displayNode.GetGlyphScale()
            node['markups'] = []
            for markupIndex in range(markupsNode.GetNumberOfMarkups()):
                position = [0, ] * 3
                markupsNode.GetNthFiducialPosition(markupIndex, position)
                position
                node['markups'].append({
                    'label': markupsNode.GetNthFiducialLabel(markupIndex),
                    'position': position
                })
            fiducials[markupsNode.GetID()] = node
        return (json.dumps(fiducials).encode())

    def fiducial(self, request, requestBody):
        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)
        try:
            fiducialID = q['id'][0].strip()
        except KeyError:
            fiducialID = 'vtkMRMLMarkupsFiducialNode*'
        try:
            index = q['index'][0].strip()
        except KeyError:
            index = 0
        try:
            r = q['r'][0].strip()
        except KeyError:
            r = 0
        try:
            a = q['a'][0].strip()
        except KeyError:
            a = 0
        try:
            s = q['s'][0].strip()
        except KeyError:
            s = 0

        fiducialNode = slicer.util.getNode(fiducialID)
        fiducialNode.SetNthFiducialPosition(index, float(r), float(a), float(s));
        return "{'result': 'ok'}"

    def accessStudy(self, request, requestBody):
        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)

        request = json.loads(requestBody)

        dicomWebEndpoint = request['dicomWEBPrefix'] + '/' + request['dicomWEBStore']
        print(f"Loading from {dicomWebEndpoint}")

        from DICOMLib import DICOMUtils
        loadedUIDs = DICOMUtils.importFromDICOMWeb(
            dicomWebEndpoint=request['dicomWEBPrefix'] + '/' + request['dicomWEBStore'],
            studyInstanceUID=request['studyUID'],
            accessToken=request['accessToken'])

        files = []
        for studyUID in loadedUIDs:
            for seriesUID in slicer.dicomDatabase.seriesForStudy(studyUID):
                for instance in slicer.dicomDatabase.instancesForSeries(seriesUID):
                    files.append(slicer.dicomDatabase.fileForInstance(instance))
        loadables = DICOMUtils.getLoadablesFromFileLists([files])
        loadedNodes = DICOMUtils.loadLoadables(loadLoadables)

        print(f"Loaded {loadedUIDs}, and {loadedNodes}")

        return b'{"result": "ok"}'

    def mrml(self, request):
        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)
        try:
            format = q['format'][0].strip().lower()
        except KeyError:
            format = 'glTF'
        try:
            targetFiberCount = q['targetFiberCount'][0].strip().lower()
        except KeyError:
            targetFiberCount = None
        try:
            fiberMode = q['fiberMode'][0].strip().lower()
        except KeyError:
            fiberMode = 'lines'
        try:
            id_ = q['id'][0].strip().lower()
        except KeyError:
            id_ = None
        if format == 'glTF':
            nodeFilter = lambda node: True
            if id_:
                nodeFilter = lambda node: node.GetID().lower() == id_
            exporter = glTFLib.glTFExporter(slicer.mrmlScene)
            glTF = exporter.export(options={
                "nodeFilter": nodeFilter,
                "targetFiberCount": targetFiberCount,
                "fiberMode": fiberMode
            })
            self.registerOneTimeBuffers(exporter.buffers)
            return glTF.encode()
        else:
            return (json.dumps(slicer.util.getNodes('*').keys()).encode())

    def slice(self, request):
        """return a png for a slice view.
        Args:
         view={red, yellow, green}
         scrollTo= 0 to 1 for slice position within volume
         offset=mm offset relative to slice origin (position of slice slider)
         size=pixel size of output png
        """
        import vtk.util.numpy_support
        import numpy

        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)
        try:
            view = q['view'][0].strip().lower()
        except KeyError:
            view = 'red'
        options = ['red', 'yellow', 'green']
        if not view in options:
            view = 'red'
        layoutManager = slicer.app.layoutManager()
        sliceLogic = layoutManager.sliceWidget(view.capitalize()).sliceLogic()
        try:
            mode = str(q['mode'][0].strip())
        except (KeyError, ValueError):
            mode = None
        try:
            offset = float(q['offset'][0].strip())
        except (KeyError, ValueError):
            offset = None
        try:
            copySliceGeometryFrom = q['copySliceGeometryFrom'][0].strip()
        except (KeyError, ValueError):
            copySliceGeometryFrom = None
        try:
            scrollTo = float(q['scrollTo'][0].strip())
        except (KeyError, ValueError):
            scrollTo = None
        try:
            size = int(q['size'][0].strip())
        except (KeyError, ValueError):
            size = None
        try:
            orientation = q['orientation'][0].strip()
        except (KeyError, ValueError):
            orientation = None

        offsetKey = 'offset.' + view
        # if mode == 'start' or not self.interactionState.has_key(offsetKey):
        # self.interactionState[offsetKey] = sliceLogic.GetSliceOffset()

        if scrollTo:
            volumeNode = sliceLogic.GetBackgroundLayer().GetVolumeNode()
            bounds = [0, ] * 6
            sliceLogic.GetVolumeSliceBounds(volumeNode, bounds)
            sliceLogic.SetSliceOffset(bounds[4] + (scrollTo * (bounds[5] - bounds[4])))
        if offset:
            # startOffset = self.interactionState[offsetKey]
            sliceLogic.SetSliceOffset(startOffset + offset)
        if copySliceGeometryFrom:
            otherSliceLogic = layoutManager.sliceWidget(copySliceGeometryFrom.capitalize()).sliceLogic()
            otherSliceNode = otherSliceLogic.GetSliceNode()
            sliceNode = sliceLogic.GetSliceNode()
            # technique from vtkMRMLSliceLinkLogic (TODO: should be exposed as method)
            sliceNode.GetSliceToRAS().DeepCopy(otherSliceNode.GetSliceToRAS())
            fov = sliceNode.GetFieldOfView()
            otherFOV = otherSliceNode.GetFieldOfView()
            sliceNode.SetFieldOfView(otherFOV[0],
                                     otherFOV[0] * fov[1] / fov[0],
                                     fov[2]);

        if orientation:
            sliceNode = sliceLogic.GetSliceNode()
            previousOrientation = sliceNode.GetOrientationString().lower()
            if orientation.lower() == 'axial':
                sliceNode.SetOrientationToAxial()
            if orientation.lower() == 'sagittal':
                sliceNode.SetOrientationToSagittal()
            if orientation.lower() == 'coronal':
                sliceNode.SetOrientationToCoronal()
            if orientation.lower() != previousOrientation:
                sliceLogic.FitSliceToAll()

        imageData = sliceLogic.GetBlend().Update(0)
        imageData = sliceLogic.GetBlend().GetOutputDataObject(0)
        pngData = []
        if imageData:
            pngData = self.vtkImageDataToPNG(imageData)
        self.logMessage('returning an image of %d length' % len(pngData))
        return pngData

    def threeD(self, request):
        """return a png for a threeD view
        Args:
         view={nodeid} (currently ignored)
         mode= (currently ignored)
         lookFromAxis = {L, R, A, P, I, S}
        """
        import numpy
        import vtk.util.numpy_support

        p = urlparse.urlparse(request)
        q = urlparse.parse_qs(p.query)
        try:
            view = q['view'][0].strip().lower()
        except KeyError:
            view = '1'
        try:
            lookFromAxis = q['lookFromAxis'][0].strip().lower()
        except KeyError:
            lookFromAxis = None
        try:
            size = int(q['size'][0].strip())
        except (KeyError, ValueError):
            size = None
        try:
            mode = str(q['mode'][0].strip())
        except (KeyError, ValueError):
            mode = None
        try:
            roll = float(q['roll'][0].strip())
        except (KeyError, ValueError):
            roll = None
        try:
            panX = float(q['panX'][0].strip())
        except (KeyError, ValueError):
            panX = None
        try:
            panY = float(q['panY'][0].strip())
        except (KeyError, ValueError):
            panY = None
        try:
            orbitX = float(q['orbitX'][0].strip())
        except (KeyError, ValueError):
            orbitX = None
        try:
            orbitY = float(q['orbitY'][0].strip())
        except (KeyError, ValueError):
            orbitY = None

        layoutManager = slicer.app.layoutManager()
        view = layoutManager.threeDWidget(0).threeDView()
        view.renderEnabled = False

        if lookFromAxis:
            axes = ['None', 'r', 'l', 's', 'i', 'a', 'p']
            try:
                axis = axes.index(lookFromAxis[0])
                view.lookFromViewAxis(axis)
            except ValueError:
                pass

        if False and mode:
            # TODO: 'statefull' interaction with the camera
            # - save current camera when mode is 'start'
            # - increment relative to the start camera during interaction
            cameraNode = slicer.util.getNode('*Camera*')
            camera = cameraNode.GetCamera()
            # if mode == 'start' or not self.interactionState.has_key('camera'):
            # startCamera = vtk.vtkCamera()
            # startCamera.DeepCopy(camera)
            # self.interactionState['camera'] = startCamera
            # startCamera = self.interactionState['camera']
            cameraNode.DisableModifiedEventOn()
            camera.DeepCopy(startCamera)
            if roll:
                camera.Roll(roll * 100)
            position = numpy.array(startCamera.GetPosition())
            focalPoint = numpy.array(startCamera.GetFocalPoint())
            viewUp = numpy.array(startCamera.GetViewUp())
            viewPlaneNormal = numpy.array(startCamera.GetViewPlaneNormal())
            viewAngle = startCamera.GetViewAngle()
            viewRight = numpy.cross(viewUp, viewPlaneNormal)
            viewDistance = numpy.linalg.norm(focalPoint - position)
            self.logMessage("position", position)
            self.logMessage("focalPoint", focalPoint)
            self.logMessage("viewUp", viewUp)
            self.logMessage("viewPlaneNormal", viewPlaneNormal)
            self.logMessage("viewAngle", viewAngle)
            self.logMessage("viewRight", viewRight)
            self.logMessage("viewDistance", viewDistance)
            if panX and panY:
                offset = viewDistance * -panX * viewRight + viewDistance * viewUp * panY
                newPosition = position + offset
                newFocalPoint = focalPoint + offset
                camera.SetPosition(newPosition)
                camera.SetFocalPoint(newFocalPoint)
            if orbitX and orbitY:
                offset = viewDistance * -orbitX * viewRight + viewDistance * viewUp * orbitY
                newPosition = position + offset
                newFPToEye = newPosition - focalPoint

                newPosition = focalPoint + viewDistance * newFPToEye / numpy.linalg.norm(newFPToEye)
                camera.SetPosition(newPosition)
            cameraNode.DisableModifiedEventOff()
            cameraNode.InvokePendingModifiedEvent()

        view.renderWindow().Render()
        view.renderEnabled = True
        view.forceRender()
        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(view.renderWindow())
        w2i.SetReadFrontBuffer(0)
        w2i.Update()
        imageData = w2i.GetOutput()

        pngData = self.vtkImageDataToPNG(imageData)
        self.logMessage('threeD returning an image of %d length' % len(pngData))
        return pngData

    def timeimage(self, request=''):
        """For debugging - return an image with the current time
        rendered as text down to the hundredth of a second"""

        # check arguments
        p = urlparse.urlparse(request.decode())
        q = urlparse.parse_qs(p.query)
        try:
            color = "#" + q['color'][0].strip().lower()
        except KeyError:
            color = "#330"

        #
        # make a generally transparent image,
        #
        imageWidth = 128
        imageHeight = 32
        timeImage = qt.QImage(imageWidth, imageHeight, qt.QImage().Format_ARGB32)
        timeImage.fill(0)

        # a painter to use for various jobs
        painter = qt.QPainter()

        # draw a border around the pixmap
        painter.begin(timeImage)
        pen = qt.QPen()
        color = qt.QColor(color)
        color.setAlphaF(0.8)
        pen.setColor(color)
        pen.setWidth(5)
        pen.setStyle(3)  # dotted line (Qt::DotLine)
        painter.setPen(pen)
        rect = qt.QRect(1, 1, imageWidth - 2, imageHeight - 2)
        painter.drawRect(rect)
        color = qt.QColor("#333")
        pen.setColor(color)
        painter.setPen(pen)
        position = qt.QPoint(10, 20)
        text = str(time.time())  # text to draw
        painter.drawText(position, text)
        painter.end()

        # convert the image to vtk, then to png from there
        vtkTimeImage = vtk.vtkImageData()
        slicer.qMRMLUtils().qImageToVtkImageData(timeImage, vtkTimeImage)
        pngData = self.vtkImageDataToPNG(vtkTimeImage)
        return pngData
