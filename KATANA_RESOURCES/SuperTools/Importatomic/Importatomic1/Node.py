from Katana import weakref, itertools, Utils, NodegraphAPI, UniqueName
import logging

log = logging.getLogger('Importatomic.Node')
NodegraphAPI.AddNodeFlavor('Importatomic', '3d')


class ImportatomicNode(NodegraphAPI.SuperTool):

    def __init__(self):
        self.hideNodegraphGroupControls()
        self.addOutputPort('default')
        self.getParameters().parseXML('\n'
                                      '<group_parameter>\n'
                                      '<string_parameter name="__nodePanel" value="Importatomic"/>\n'
                                      '<number_parameter name="__pluginRevision" value="1"/>\n'
                                      '</group_parameter>')
        subGroup = NodegraphAPI.CreateNode('Group', self)
        subGroup.addOutputPort('out')
        subGroup.getOutputPortByIndex(0).connect(self.getReturnPort('default'))
        merge = NodegraphAPI.CreateNode('Merge', subGroup)
        merge.getOutputPortByIndex(0).connect(subGroup.getReturnPort('out'))

    def polish(self):
        pass

    def __getNodeConnectedToGroupPort(self, groupNode, portName):
        port = groupNode.getReturnPort(portName)
        if not port:
            return None
        connectedPort = port.getConnectedPort(0)
        if not connectedPort:
            return None
        connectedNode = connectedPort.getNode()
        return connectedNode

    def getMergeNodeForOutput(self, outputName):
        outputGroup = self.__getNodeConnectedToGroupPort(self, outputName)
        if not outputGroup:
            return None
        port = outputGroup.getOutputPortByIndex(0)
        if not port:
            return None
        mergeNode = self.__getNodeConnectedToGroupPort(outputGroup, port.getName())
        if not mergeNode:
            return None
        if mergeNode.getType() != 'Merge':
            inputPort = mergeNode.getInputPortByIndex(0)
            if not inputPort:
                return None
            connectedPort = inputPort.getConnectedPort(0)
            if not connectedPort:
                return None
            mergeNode = connectedPort.getNode()
            if not mergeNode or mergeNode.getType() != 'Merge':
                return None
        return mergeNode

    def getFilterAssetStackOutput(self, outputName, build=False):
        outputGroup = self.__getNodeConnectedToGroupPort(self, outputName)
        if not outputGroup:
            if build:
                raise TypeError("Output port '%s' doesn't exist" % outputName)
            return None
        port = outputGroup.getOutputPortByIndex(0)
        if not port:
            return None
        node = self.__getNodeConnectedToGroupPort(outputGroup, port.getName())
        if not node:
            if build:
                raise TypeError('Internal Importatomic graph error')
            return None
        if node.getBaseType() == 'GroupStack':
            return node
        if not build:
            return None
        stack = NodegraphAPI.CreateNode('GroupStack', outputGroup)
        mergeOutputPort = node.getOutputPortByIndex(0)
        mergeConnectedPort = mergeOutputPort.getConnectedPort(0)
        mergeOutputPort.disconnect(mergeConnectedPort)
        stack.getInputPortByIndex(0).connect(mergeOutputPort)
        stack.getOutputPortByIndex(0).connect(mergeConnectedPort)
        NodegraphAPI.SetNodePosition(stack, (0, -100))
        return stack

    def getProductStructureForOutput(self, outputName):
        result = []
        merge = self.getMergeNodeForOutput(outputName)
        if not merge:
            return result
        for port in merge.getInputPorts():
            connectedPort = port.getConnectedPort(0)
            if not connectedPort:
                continue
            result.append(connectedPort.getNode())

        return result

    def layoutContents(self):
        try:
            from Katana import DrawingModule
        except:
            return

        subGroups = []
        widths = []
        for outputName in [ x.getName() for x in self.getOutputPorts() ]:
            subGroup = self.__getNodeConnectedToGroupPort(self, outputName)
            if not subGroup or subGroup.getType() != 'Group':
                continue
            bounds = DrawingModule.nodeWorld_getBoundsOfListOfNodes([
             subGroup])
            subGroups.append(subGroup)
            widths.append(bounds[2] - bounds[0])

        maxWidth = reduce(max, widths, 0) + 40
        x = 0
        for subGroup in subGroups:
            NodegraphAPI.SetNodePosition(subGroup, (x, 0))
            x += maxWidth
            self.__layoutOutputGroupContents(subGroup)

    def __layoutOutputGroupContents(self, subGroup):
        try:
            from Katana import DrawingModule
        except:
            return

        portName = subGroup.getOutputPortByIndex(0).getConnectedPort(0).getName()
        merge = self.getMergeNodeForOutput(portName)
        if not merge or merge.getType() != 'Merge':
            return
        nodes = []
        widths = []
        for port in merge.getInputPorts():
            connectedPort = port.getConnectedPort(0)
            if not connectedPort:
                continue
            node = connectedPort.getNode()
            nodes.append(node)
            bounds = DrawingModule.nodeWorld_getBoundsOfListOfNodes([node])
            widths.append(bounds[2] - bounds[0])

        NodegraphAPI.SetNodePosition(merge, (0, 0))
        maxWidth = reduce(max, widths, 0) + 10
        x = maxWidth * (len(widths) - 1) / -2.0
        for node in nodes:
            NodegraphAPI.SetNodePosition(node, (x, 100))
            x += maxWidth

    def addOutput(self, desiredName):
        port = self.addOutputPort(desiredName)
        returnPort = self.getReturnPort(port.getName())
        subGroup = NodegraphAPI.CreateNode('Group', self)
        subGroup.addOutputPort('out')
        subGroup.getOutputPortByIndex(0).connect(returnPort)
        merge = NodegraphAPI.CreateNode('Merge', subGroup)
        merge.getOutputPortByIndex(0).connect(subGroup.getReturnPort('out'))
        return port.getName()

    def removeOutput(self, outputName):
        port = self.getOutputPort(outputName)
        if not port:
            return
        if port.getName() == 'default':
            return
        for connectedPort in port.getConnectedPorts():
            port.disconnect(connectedPort)

        subgroup = self.__getNodeConnectedToGroupPort(self, outputName)
        returnPort = self.getReturnPort(outputName)
        for connectedPort in returnPort.getConnectedPorts():
            returnPort.disconnect(connectedPort)

        if subgroup:
            subgroup.delete()
        self.removeOutputPort(outputName)

    def reorderOutput(self, fromIndex, toIndex):
        if fromIndex == 0:
            return
        if toIndex == 0:
            return
        if toIndex > fromIndex:
            toIndex -= 1
        port = self.getOutputPortByIndex(fromIndex)
        if not port:
            return
        portName = port.getName()
        subGroup = self.__getNodeConnectedToGroupPort(self, portName)
        if not subGroup:
            return
        for i in subGroup.getOutputPortByIndex(0).getConnectedPorts():
            subGroup.getOutputPortByIndex(0).disconnect(i)

        self.removeOutputPort(portName)
        del port
        newPort = self.addOutputPortAtIndex(portName, toIndex)
        returnPort = self.getReturnPort(portName)
        subGroup.getOutputPortByIndex(0).connect(returnPort)

    def insertNodeIntoOutputMerge(self, productNode, outputName, toIndex=-1):
        merge = self.getMergeNodeForOutput(outputName)
        if not merge:
            return
        for port in productNode.getInputPorts() + productNode.getOutputPorts():
            for connectedPort in port.getConnectedPorts():
                port.disconnect(connectedPort)

        productNode.setParent(merge.getParent())
        port = merge.addInputPortAtIndex('i0', toIndex)
        productNode.getOutputPortByIndex(0).connect(port)

    def removeNodeFromOutputMerge(self, productNode):
        productNodeParent = productNode.getParent()
        if not productNodeParent:
            return
        if productNodeParent.getParent() != self:
            return
        connectedPort = productNode.getOutputPortByIndex(0).getConnectedPort(0)
        if not connectedPort:
            return
        merge = connectedPort.getNode()
        if merge.getType() != 'Merge':
            return
        productNode.getOutputPortByIndex(0).disconnect(connectedPort)
        merge.removeInputPort(connectedPort.getName())
        return productNode