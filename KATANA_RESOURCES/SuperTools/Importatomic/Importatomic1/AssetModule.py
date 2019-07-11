__all__ = ['AssetModule', 'AssetTreeChild']
from Constants import *
from Katana import NodegraphAPI

import os, logging
log = logging.getLogger('Importatomic.AssetModule')


class AssetModule(object):
    __typeFactory = {}
    __addCallbacks = {}
    __postAddCallbacks = {}
    __batchAddCallbacks = {}
    __utilCallbacks = {}

    @classmethod
    def RegisterType(cls, typeName, handler):
        cls.__typeFactory[typeName] = handler

    @classmethod
    def GetAllRegisteredHandlers(cls):
        return cls.__typeFactory.values()

    @staticmethod
    def GetAssetType(node):
        typeParam = node.getParameter('__importatomicType')
        if not typeParam:
            return node.getType()
        return typeParam.getValue(0)

    @staticmethod
    def SetAssetType(node, typeName):
        typeParam = node.getParameter('__importatomicType')
        if not typeParam:
            node.getParameters().parseXML("\n"
                                          "<group_parameter>\n"
                                          "<string_parameter name='__importatomicType'/>\n"
                                          "</group_parameter>\n"
                                          )
            typeParam = node.getParameter('__importatomicType')
            typeParam.setHintString(str({'widget': 'null'}))
        typeParam.setValue(typeName, 0)

    @staticmethod
    def GetCustomAssetName(node, paramName='__importatomicName'):
        if not node:
            return
        param = node.getParameter(paramName)
        if not param:
            return
        value = param.getValue(0).strip()
        if value:
            return value
        return

    @staticmethod
    def SetCustomAssetName(node, assetName, paramName='__importatomicName'):
        param = node.getParameter(paramName)
        if not assetName and not param:
            return
        if not param:
            node.getParameters().parseXML("\n<group_parameter>"
                                          "\n<string_parameter name='%s' "
                                          "hints='{&apos;widget&apos;: &apos;null&apos;}'/>"
                                          "\n</group_parameter>"
                                          "\n" % paramName)
            param = node.getParameter(paramName)
        if param.getValue(0) == assetName:
            return
        param.setValue(assetName, 0)

    @classmethod
    def GetHandlerForType(cls, typeName):
        if typeName in cls.__typeFactory:
            return cls.__typeFactory[typeName]
        return AssetModule()

    @classmethod
    def GetHandlerForNode(cls, node):
        return cls.GetHandlerForType(cls.GetAssetType(node))

    @classmethod
    def GetTypeNames(cls):
        result = cls.__typeFactory.keys()
        result.sort()
        return result

    @classmethod
    def RegisterCreateCallback(cls, name, callback, postCallback=None):
        cls.__addCallbacks[name] = callback
        cls.__postAddCallbacks[name] = postCallback

    @classmethod
    def RegisterBatchCreateCallback(cls, filetype, callback):
        cls.__batchAddCallbacks[filetype] = callback

    @classmethod
    def GetCreateCallbackNames(cls):
        result = cls.__addCallbacks.keys()
        result.sort()
        return result

    @classmethod
    def TriggerCreateCallback(cls, name, node):
        callback = cls.__addCallbacks.get(name)
        if callable(callback):
            return callback(node)

    @classmethod
    def TriggerPostCreateCallback(cls, name, node, nodesAdded):
        callback = cls.__postAddCallbacks.get(name)
        if callable(callback):
            return callback(node, nodesAdded)

    @classmethod
    def TriggerBatchCreateCallback(cls, filetype, node, assetId, locationExpression):
        callback = cls.__batchAddCallbacks.get(filetype)
        if callable(callback):
            return callback(node, assetId, locationExpression)

    @classmethod
    def HasBatchCreateCallback(cls, filetype):
        hasBatchCreateCallback = filetype in cls.__batchAddCallbacks
        return hasBatchCreateCallback

    @classmethod
    def GetBatchCreateCallback(cls):
        result = cls.__batchAddCallbacks.keys()
        result.sort()
        return result

    @classmethod
    def RegisterUtilCallback(cls, name, callback):
        cls.__utilCallbacks[name] = callback

    @classmethod
    def GetUtilCallbackNames(cls):
        result = cls.__utilCallbacks.keys()
        result.sort()
        return result

    def setItemState(self, node, item):
        item.setText(NAME_COLUMN, node.getName())
        # item.setText(TYPE_COLUMN, node.getType())
        # item.setText(STATUS_COLUMN, '')
        log.debug('setItemState(): node = %s' % node.getName())

    def getEditor(self, node, widgetParent):
        from Katana import UI4
        policy = UI4.FormMaster.CreateParameterPolicy(None, node.getParameters())
        w = UI4.FormMaster.KatanaFactory.ParameterWidgetFactory.buildWidget(widgetParent, _GetHideTitlePolicy()(policy))
        w.showPopdown(True)
        return w

    def addToContextMenu(self, menu, importatomicNode, node):
        pass

    def getPrimarySpref(self, node):
        return None

    def setPrimarySprefVersion(self, node, version):
        pass

    def getSecondarySprefList(self, node):
        return ()

    def setSecondarySprefVersion(self, node, index, version):
        log.debug('setSecondarySprefVersion(): %s, %s, %s' % (
         node, index, version))

    def setSecondaryItemState(self, node, item, index):
        pass

    def freeze(self):
        pass

    def thaw(self):
        pass

    def getAssetTreeRoot(self, node):
        return None


class AssetTreeChild(object):

    def setItemState(self, item):
        pass

    def isSelectable(self):
        return False

    def isDraggable(self):
        return False

    def getAssetId(self):
        return None

    def setAssetId(self, assetId):
        pass

    def isVersionSettable(self):
        return True

    def getChildren(self):
        pass

    def acceptsDrop(self, dropItem, index):
        return False

    def acceptDrop(self, dropItem, index):
        return False

    def getEditor(self, widgetParent):
        return None

    def getItemKey(self):
        return self

    def isIgnorable(self):
        return False

    def isIgnored(self):
        return False

    def setIgnored(self, state):
        pass

    def isDeletable(self):
        return False

    def delete(self):
        pass

    def canDuplicate(self):
        return False

    def duplicateItem(self):
        pass

    def addToContextMenu(self, menu, importatomicNode):
        pass

    def addNodeObservers(self, callback):
        pass

    def getDefaultOpenState(self):
        return True

    def getCustomVersionTagNames(self):
        return []

    def hasError(self):
        return False


def _GetHideTitlePolicy():
    global _HideTitlePolicy
    if _HideTitlePolicy:
        return _HideTitlePolicy
    from Katana import QT4FormWidgets

    class HideTitlePolicy(QT4FormWidgets.ValuePolicyProxy):

        def __init__(self, policy):
            QT4FormWidgets.ValuePolicyProxy.__init__(self, policy)

        def shouldDisplayWrench(self):
            return False

        def getWidgetHints(self):
            return {'hideTitle': 'True'}

    _HideTitlePolicy = HideTitlePolicy
    return _HideTitlePolicy


_HideTitlePolicy = None