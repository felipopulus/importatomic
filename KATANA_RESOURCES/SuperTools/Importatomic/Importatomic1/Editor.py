from Katana import os, Utils, QtCore, QtGui, QtWidgets, UI4, QT4FormWidgets, Callbacks, AssetAPI
from Katana import NodegraphAPI
from UI4 import Widgets
import UI4
from AssetModule import *
from Constants import *
import logging
log = logging.getLogger('Importatomic.Editor')


class ImportatomicEditor(QtWidgets.QWidget):
    def __init__(self, parent, node):
        self.__node = node
        QtWidgets.QWidget.__init__(self, parent)
        mainLayout = QtWidgets.QVBoxLayout(self)
        self.__menuBar = QtWidgets.QMenuBar(self)
        self.__addMenu = self.__menuBar.addMenu(UI4.Util.IconManager.GetIcon('Icons/plus16.png'), 'Add')
        self.__addMenu.aboutToShow.connect(self.__addMenuAboutToShow)
        self.__addMenu.triggered.connect(self.__addMenuTriggered)
        mainLayout.setMenuBar(self.__menuBar)
        mainLayout.setSpacing(0)
        self.__listContainer = QtWidgets.QFrame(self)
        mainLayout.addWidget(self.__listContainer)
        self.__listStretchBox = UI4.Widgets.StretchBox(self.__listContainer, allowHorizontal=False, allowVertical=True)
        self.__tree = UI4.Widgets.SortableTreeWidget(None)
        self.__versionPopup = Widgets.FilterablePopup()
        self.__lastTreePos = QtCore.QPoint(0, 0)
        self.__listStretchBox.layout().addWidget(self.__tree)
        self.__listStretchBox.setMinHeight(160)
        self.__listStretchBox.setFixedHeight(160)
        mainLayout.addWidget(self.__listStretchBox)
        self.__headerLabels = ['Name', 'Type', 'Version', 'Resolved Version', 'Status']
        self.__tree.setColumnCount(len(self.__headerLabels))
        self.__tree.setHeaderLabels(self.__headerLabels)
        self.__tree.header().setSectionsClickable(False)
        self.__tree.setSelectionMode(self.__tree.ExtendedSelection)
        self.__tree.setRootIsDecorated(True)
        self.__tree.setDraggable(True)
        self.__tree.setAllColumnsShowFocus(True)
        self.__tree.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.__tree.setMinimumHeight(128)
        self.__tree.dragMoveEventSignal.connect(self.__dragMoveEventCallback)
        self.__tree.dropEventSignal.connect(self.__dropEventCallback)
        self.__tree.aboutToDrag.connect(self.__aboutToDragCallback)
        self.__tree.itemSelectionChanged.connect(self.__selectionChanged)
        self.__tree.mousePressEventSignal.connect(self.__listMousePressEvent)
        self.__tree.keyPressEventSignal.connect(self.__listKeyPressCallback)
        self.__versionPopup.itemChosen.connect(self.__popupVersionsItemChosen)
        self.__selectionStateDisplay = EditorStatusWidget(self)
        mainLayout.addWidget(self.__selectionStateDisplay)
        self.__selectionStateDisplay.customNameStateChange.connect(self.__customNameStateChanged)
        self.__selectionStateDisplay.customNameFieldChange.connect(self.__customNameChanged)
        self.__parameterDisplayArea = QtWidgets.QWidget(self)
        QtWidgets.QVBoxLayout(self.__parameterDisplayArea)
        mainLayout.addWidget(self.__parameterDisplayArea)
        mainLayout.addStretch()
        self.__additionalObservedNodes = {}
        self.__addObserverNode(NodegraphAPI.GetRootNode())
        self.__frozen = True
        self.__preselect = None
        self.__primaryProductDict = {}
        self.__rebuilding = False
        self.__addDupsDialog = None
        self.__currentDisplayWidgetSource = None
        self.__currentDisplayWidget = None
        return

    __EVENTNAMES = ('cacheManager_flush', 'parameter_finalizeValue', 'port_disconnect',
                    'port_connect', 'node_renameOutputPort', 'node_setBypassed',
                    'nodegraph_defaultPluginsChanged')

    def __registerEvents(self):
        for name in self.__EVENTNAMES:
            Utils.EventModule.RegisterCollapsedHandler(self.__collapsedEventHander, name)

    def __unregisterEvents(self):
        for name in self.__EVENTNAMES:
            Utils.EventModule.UnregisterCollapsedHandler(self.__collapsedEventHander, name)

    def __addObserverNode(self, node):
        key = hash(node)
        if key in self.__additionalObservedNodes:
            self.__additionalObservedNodes[key] += 1
        else:
            self.__additionalObservedNodes[key] = 1

    def __removeObserverNode(self, node):
        key = hash(node)
        if key in self.__additionalObservedNodes:
            self.__additionalObservedNodes[key] -= 1
            if self.__additionalObservedNodes[key] < 1:
                del self.__additionalObservedNodes[key]

    def __nodeIsMine(self, node):
        while node:
            if node == self.__node:
                return True
            if hash(node) in self.__additionalObservedNodes:
                return True
            node = node.getParent()

        return False

    def __collapsedEventHander(self, args):
        update = False
        for eventType, _eventID, kwargs in args:
            if eventType == 'parameter_finalizeValue':
                node = kwargs['node']
                if self.__nodeIsMine(node):
                    update = True
            else:
                if eventType in ('port_connect', 'port_disconnect'):
                    for nodeNameKey in ('nodeNameA', 'nodeNameB'):
                        nodeName = kwargs[nodeNameKey]
                        node = NodegraphAPI.GetNode(nodeName)
                        if self.__nodeIsMine(node):
                            update = True
                            break

                else:
                    if eventType == 'node_setBypassed':
                        node = kwargs['node']
                        if self.__nodeIsMine(node):
                            update = True
                    else:
                        if eventType == 'node_renameOutputPort':
                            if kwargs['node'] == self.__node:
                                update = True
                        else:
                            if eventType == 'nodegraph_defaultPluginsChanged':
                                update = True
                            else:
                                if eventType == 'cacheManager_flush':
                                    update = True
            if update:
                break

        if update:
            self.__updateList()

    def showEvent(self, event):
        QtWidgets.QWidget.showEvent(self, event)
        if self.__frozen:
            self.__frozen = False
            self._thaw()

    def hideEvent(self, event):
        QtWidgets.QWidget.hideEvent(self, event)
        if not self.__frozen:
            self.__frozen = True
            self._freeze()

    def _thaw(self):
        self.__registerEvents()
        self.__updateList()
        for handler in AssetModule.GetAllRegisteredHandlers():
            handler.thaw()

    def _freeze(self):
        self.__unregisterEvents()
        for handler in AssetModule.GetAllRegisteredHandlers():
            handler.freeze()

    def __updateList(self):
        self.__rebuilding = True
        self.__primaryProductDict = {}
        horzScrollbar = self.__tree.horizontalScrollBar()
        if horzScrollbar and horzScrollbar.isVisible():
            posx = horzScrollbar.value()
        else:
            horzScrollbar = None
        vertScrollbar = self.__tree.verticalScrollBar()
        if vertScrollbar and vertScrollbar.isVisible():
            posy = vertScrollbar.value()
        else:
            vertScrollbar = None
        selectedTable, openTable = self.__tree.getExpandedAndSelectionTables()
        selectedKeys = set((x.getItemData().get('key') for x in selectedTable.itervalues()))
        if self.__preselect:
            selectedKeys = self.__preselect[:]
            self.__preselect = None
        openState = {}
        for path, (state, item) in openTable.iteritems():
            openState[item.getItemData().get('key')] = state

        self.__additionalObservedNodes.clear()
        self.__addObserverNode(NodegraphAPI.GetRootNode())
        self.__tree.clear()
        for port in self.__node.getOutputPorts():
            outputName = port.getName()
            outputItem = UI4.Widgets.SortableTreeWidgetItem(self.__tree, outputName)
            outputItem.setIcon(0, UI4.Util.IconManager.GetIcon('Icons/port16.png'))
            outputItem.setItemData({'type': 'output', 'port': port, 'key': port})
            outputItem.setExpanded(openState.get(port, True))
            if port in selectedKeys:
                outputItem.setSelected(True)
            for node in self.__node.getProductStructureForOutput(outputName):
                handler = AssetModule.GetHandlerForNode(node)
                rootAsset = handler.getAssetTreeRoot(node)
                if rootAsset:
                    item = self.__traverseItemTree(rootAsset, outputItem, selectedKeys, openState, node)
                    item.getItemData()['node'] = node
                    currentAssetName = handler.GetCustomAssetName(node, '__currentName')
                    if currentAssetName:
                        item.setText(NAME_COLUMN, currentAssetName)
                    customAssetName = handler.GetCustomAssetName(node)
                    if customAssetName:
                        item.setText(NAME_COLUMN, customAssetName)
                    continue

        if horzScrollbar:
            horzScrollbar.setValue(posx)
        if vertScrollbar:
            vertScrollbar.setValue(posy)
        self.__rebuilding = False
        self.__selectionChanged()
        return

    def __traverseItemTree(self, assetItem, treeParent, selectedKeys, openState, node=None):
        item = AssetListViewItem(treeParent, '')
        key = node
        selectable = True
        if not node:
            try:
                key = assetItem.getItemKey()
                selectable = assetItem.isSelectable()
            except Exception as exception:
                log.exception('Error accessing asset item %s: %s' % (
                 assetItem, str(exception)))

        item.setItemData({'type': 'assetTree', 'assetItem': assetItem, 
           'key': key})
        if selectable:
            item.setSelected(key in selectedKeys)
            item.setFlags(QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled))
        else:
            item.setFlags(QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled))
        defaultState = assetItem.getDefaultOpenState()
        expanded = openState.get(key, defaultState)
        item.setExpanded(expanded)
        try:
            assetId = assetItem.getAssetId()
            if assetId:
                assetPlugin = AssetAPI.GetDefaultAssetPlugin()
                if assetPlugin.isAssetId(assetId):
                    fields = assetPlugin.getAssetFields(assetId, True)
                    version = fields.get('version', None)
                    resolvedVersion = assetPlugin.resolveAssetVersion(assetId, throwOnError=True)
                    if version:
                        item.setText(VERSION_COLUMN, version)
                        item.setIcon(VERSION_COLUMN, UI4.Util.IconManager.GetIcon('Icons/heightAdjustDownHilite16.png'))
                    if resolvedVersion:
                        item.setText(RESOLVED_VERSION_COLUMN, resolvedVersion)
        except Exception as exception:
            log.exception('Error getting version of asset item %s: %s' % (
             assetItem, str(exception)))

        try:
            assetItem.setItemState(item)
        except Exception as exception:
            log.exception('Error setting state of asset item %s: %s' % (
             assetItem, str(exception)))

        if assetItem.isIgnorable() and assetItem.isIgnored():
            item.setIcon(NAME_COLUMN, UI4.Util.IconManager.GetIcon('Icons/ignore16.png'))
        try:
            children = assetItem.getChildren()
            if children:
                for child in children:
                    self.__traverseItemTree(child, item, selectedKeys, openState)

        except Exception as exception:
            log.exception('Error traversing children of asset item %s: %s' % (
             assetItem, str(exception)))

        try:
            assetItem.addNodeObservers(self.__addObserverNode)
        except Exception as exception:
            log.exception('Error adding node observer to asset item %s: %s' % (
             assetItem, str(exception)))

        return item

    def __selectionChanged(self):
        if self.__rebuilding:
            return
        selectedItems = self.__tree.selectedItems()
        if not selectedItems:
            self.__clearParameterArea()
            self.__selectionStateDisplay.update('', None)
            return
        if len(selectedItems) > 1:
            self.__clearParameterArea()
            self.__selectionStateDisplay.update('(%i items selected)' % len(selectedItems), None)
            return
        item = selectedItems[0]
        potentialCustomName = False
        activeCustomName = False
        itemType = item.getItemData()['type']
        itemName = str(item.text(NAME_COLUMN))
        if itemType == 'output':
            itemKey = item.getItemData()['port']
        else:
            node = itemKey = item.getItemData().get('node')
            if not itemKey and item.getItemData().get('type') == 'assetTree':
                itemKey = item.getItemData()['assetItem'].getItemKey()
            if item.parent() and item.parent().getItemData()['type'] == 'output':
                potentialCustomName = True
            if node:
                activeCustomName = AssetModule.GetCustomAssetName(node) is not None
        self.__selectionStateDisplay.update(itemName, item.icon(NAME_COLUMN), potentialCustomName, activeCustomName)
        if itemKey != self.__currentDisplayWidgetSource:
            self.__clearParameterArea()
        else:
            if isinstance(self.__currentDisplayWidget, PortEditorWidget):
                self.__currentDisplayWidget.setText(itemKey.getName())
            return
        editor = None
        if itemType == 'assetTree':
            assetItem = item.getItemData()['assetItem']
            try:
                editor = assetItem.getEditor(self.__parameterDisplayArea)
            except Exception as exception:
                log.exception('Error getting editor for asset item %s: %s' % (
                 assetItem, str(exception)))

        if not editor:
            if isinstance(itemKey, NodegraphAPI.Node):
                handler = AssetModule.GetHandlerForNode(itemKey)
                editor = handler.getEditor(itemKey, self.__parameterDisplayArea)
            elif isinstance(itemKey, NodegraphAPI.Port):
                editor = PortEditorWidget(self.__parameterDisplayArea, self.__node, itemKey.getName())
        if editor:
            editor.show()
            self.__parameterDisplayArea.layout().addWidget(editor)
            self.__currentDisplayWidget = editor
            self.__currentDisplayWidgetSource = itemKey
        return

    def __clearParameterArea(self):
        self.__currentDisplayWidgetSource = None
        if not self.__currentDisplayWidget:
            return
        self.__currentDisplayWidget.setParent(None)
        self.__currentDisplayWidget = None
        return

    def __addMenuAboutToShow(self):
        self.__addMenu.clear()
        for name in AssetModule.GetCreateCallbackNames():
            self.__addMenu.addAction(name)

        self.__addMenu.addSeparator()
        self.__addMenu.addAction('Add New Output', self.__addOutputCallback)

    def __addMenuTriggered(self, action):
        name = str(action.text())
        Utils.UndoStack.OpenGroup('%s In %s' % (
         name, self.__node.getName()))
        try:
            result = AssetModule.TriggerCreateCallback(name, self.__node)
            if isinstance(result, NodegraphAPI.Node):
                result = [
                 result]
            if not isinstance(result, list):
                return
            includedNodes = []
            productDict = self.__primaryProductDict.copy()
            for node in [ x for x in result if isinstance(x, NodegraphAPI.Node) ]:
                includedNodes.append(node)

            portName = 'default'
            selectedItems = self.__tree.selectedItems()
            if selectedItems:
                item = selectedItems[0]
                while item.parent():
                    item = item.parent()

                portName = item.getItemData()['port'].getName()
            for node in includedNodes:
                self.__node.insertNodeIntoOutputMerge(node, portName, -1)

            if includedNodes:
                self.__node.layoutContents()
            AssetModule.TriggerPostCreateCallback(name, self.__node, includedNodes)
            self.__preselect = includedNodes[:]
        except Exception as exception:
            log.exception('Error in callback of menu item action "%s": %s' % (
             name, str(exception)))
        finally:
            Utils.UndoStack.CloseGroup()

    def __addOutputCallback(self):
        Utils.UndoStack.OpenGroup('Add Output To %s' % self.__node.getName())
        try:
            self.__node.addOutput('out')
            self.__node.layoutContents()
        finally:
            Utils.UndoStack.CloseGroup()

    def __dragMoveEventCallback(self, event, parent, index, callbackRecord):
        if event.source() != self.__tree:
            return
        dragItems = self.__tree.getDragItems()
        if not dragItems:
            return
        dragItem = dragItems[0]
        if event.mimeData().hasFormat('importatomic/assettree'):
            if not parent:
                return
            d = parent.getItemData()
            if not d['type'] == 'assetTree':
                return
            assetItem = d['assetItem']
            try:
                if assetItem.acceptsDrop(dragItem.getItemData()['assetItem'], index):
                    callbackRecord.accept()
            except Exception as exception:
                log.exception('Error in drag move event callback: %s' % str(exception))

            return
        if dragItem.parent() == parent:
            dragIndex = self.__tree.findItemLocalIndex(dragItem)
            if index == dragIndex or index == dragIndex + 1:
                return
        if dragItem.parent():
            if not parent:
                return
            if not parent.parent():
                callbackRecord.accept()
                return (
                 dragItem, parent, index)
        else:
            if parent:
                return
            if index == 0:
                return
            if dragItem == self.__tree.topLevelItem(0):
                return
            callbackRecord.accept()
            return (
             dragItem, parent, index)

    def __aboutToDragCallback(self, items, dragObject):
        itemData = items[0].getItemData()
        mimeType = 'nodegraph/noderefs'
        if 'node' in itemData:
            name = itemData['node'].getName()
        else:
            if 'port' in itemData:
                name = (' ').join((x.getName() for x in self.__node.getProductStructureForOutput(itemData['port'].getName())))
            else:
                if itemData.get('type') == 'assetTree':
                    name = ''
                    mimeType = 'importatomic/assettree'
                else:
                    name = self.__node.getName()
        data = dragObject.mimeData()
        if not data:
            data = QtCore.QMimeData()
        data.setData(mimeType, name)
        if not dragObject.mimeData():
            dragObject.setMimeData(data)

    def __dropEventCallback(self, event, parent, index):
        if event.source() != self.__tree:
            return
        dragItems = self.__tree.getDragItems()
        if not dragItems:
            return
        dragItem = dragItems[0]
        if event.mimeData().hasFormat('importatomic/assettree'):
            if not parent:
                return
            d = parent.getItemData()
            if not d['type'] == 'assetTree':
                return
            assetItem = d['assetItem']
            try:
                assetItem.acceptDrop(dragItem.getItemData()['assetItem'], index)
            except Exception as exception:
                log.exception('Error accepting drop for asset item %s: %s' % (
                 assetItem, str(exception)))

            return
        toIndex = index
        fromIndex = self.__tree.findItemLocalIndex(dragItem)
        if not dragItem.parent():
            if parent:
                return
            Utils.UndoStack.OpenGroup('Reorder Output Of %s' % self.__node.getName())
            try:
                self.__node.reorderOutput(fromIndex, toIndex)
                self.__node.layoutContents()
            except Exception as exception:
                log.exception('Error reordering output of "%s" node: %s' % (
                 self.__node.getName(), str(exception)))
            finally:
                Utils.UndoStack.CloseGroup()

        else:
            if not parent:
                return
            node = dragItem.getItemData().get('node')
            if not node:
                return
            outputName = str(parent.text(NAME_COLUMN))
            Utils.UndoStack.OpenGroup('Reorder Output In %s' % self.__node.getName())
            if fromIndex < toIndex:
                toIndex = toIndex - 1
            try:
                self.__node.removeNodeFromOutputMerge(node)
                self.__node.insertNodeIntoOutputMerge(node, outputName, toIndex)
                self.__node.layoutContents()
            except Exception as exception:
                log.exception('Error reordering output in "%s" node: %s' % (
                 self.__node.getName(), str(exception)))
            finally:
                Utils.UndoStack.CloseGroup()

    def __getSingleSelectedAssetItemAndNode(self):
        selectedItems = self.__tree.selectedItems()
        if len(selectedItems) > 1:
            return (None, None)
        item = selectedItems[0]
        node = item.getItemData().get('node')
        if node:
            return (item, node)
        return (None, None)

    def __customNameStateChanged(self, state):
        item, node = self.__getSingleSelectedAssetItemAndNode()
        if not node:
            return
        Utils.UndoStack.OpenGroup('%s Custom Asset Name In %s' % (
         ('Disable', 'Enable')[state], self.__node.getName()))
        try:
            if state:
                AssetModule.SetCustomAssetName(node, str(item.text(NAME_COLUMN)))
            else:
                AssetModule.SetCustomAssetName(node, '')
        finally:
            Utils.UndoStack.CloseGroup()

    def __customNameChanged(self, name):
        item, node = self.__getSingleSelectedAssetItemAndNode()
        if not node:
            return
        Utils.UndoStack.OpenGroup('Change Custom Asset Name In %s' % (self.__node.getName(),))
        try:
            AssetModule.SetCustomAssetName(node, name)
        finally:
            Utils.UndoStack.CloseGroup()

    def __findAssetIdFromTreeItem(self, item):
        itemData = item.getItemData()
        itemType = itemData['type']
        if itemType == 'assetTree':
            assetItem = itemData['assetItem']
            assetId = assetItem.getAssetId()
            assetPlugin = AssetAPI.GetDefaultAssetPlugin()
            if assetPlugin.isAssetId(assetId):
                return assetId
        return

    def __popupVersionsItemChosen(self, chosenVersion, meta):
        item = self.__tree.itemAt(self.__lastTreePos)
        if item != None:
            itemData = item.getItemData()
            if itemData['type'] == 'assetTree':
                assetPlugin = AssetAPI.GetDefaultAssetPlugin()
                assetItem = itemData['assetItem']
                assetId = assetItem.getAssetId()
                if assetPlugin.isAssetId(assetId):
                    fields = assetPlugin.getAssetFields(assetId, False)
                    fields['version'] = str(chosenVersion)
                    assetIdWithVersion = assetPlugin.buildAssetId(fields)
                    assetItem.setAssetId(assetIdWithVersion)
        self.__versionPopup.clearFilterField()
        self.__versionPopup.clear()
        return

    def __popupVersions(self, item, local_pos, global_pos):
        currentColumnId = self.__tree.columnAt(local_pos.x())
        currentColumnName = self.__headerLabels[currentColumnId]
        if currentColumnName == 'Version':
            itemData = item.getItemData()
            itemType = itemData['type']
            if itemType == 'assetTree':
                assetItem = itemData['assetItem']
                assetId = assetItem.getAssetId()
                if assetId != None:
                    assetPlugin = AssetAPI.GetDefaultAssetPlugin()
                    if assetPlugin.isAssetId(assetId):
                        versions = []
                        customTags = assetItem.getCustomVersionTagNames()
                        if customTags:
                            versions = customTags
                        versions.extend(assetPlugin.getAssetVersions(assetId))
                        if versions:
                            self.__versionPopup.clear()
                            for version in versions:
                                self.__versionPopup.addItem(version)

                            self.__versionPopup.popup(global_pos)
                            self.__versionPopup.show()
                        return True
        return False

    def __listMousePressEvent(self, event):
        item = self.__tree.itemAt(event.pos())
        if not item:
            return
        pos = event.pos()
        pos = self.__tree.mapToGlobal(QtCore.QPoint(pos.x(), pos.y() + self.__tree.header().height()))
        self.__lastTreePos = event.pos()
        self.__lastPos = pos
        if event.button() == QtCore.Qt.LeftButton:
            local_pos = event.pos()
            global_pos = pos
            if self.__popupVersions(item, local_pos, global_pos):
                event.accept()
        else:
            if event.button() == QtCore.Qt.RightButton:
                if item.isSelected():
                    items = self.__tree.selectedItems()
                else:
                    items = [
                     item]
                for item in items:
                    dark = QtGui.QColor(32, 32, 32)
                    item.setHiliteColor(dark)
                    self.__tree.update(self.__tree.indexFromItem(item))

                menu = QtWidgets.QMenu(None)
                types = set((i.getItemData()['type'] for i in items))
                if len(types) > 1:
                    menu.addAction(RemoveItemsAction(menu, self.__node, items))
                else:
                    itemType = tuple(types)[0]
                    if itemType == 'output':
                        if str(item.text(NAME_COLUMN)) == 'default':
                            a = menu.addAction('(Default Output Cannot Be Removed)')
                            a.setEnabled(False)
                        else:
                            menu.addAction(RemoveItemsAction(menu, self.__node, items))
                    else:
                        if itemType == 'assetTree':
                            assetItem = item.getItemData()['assetItem']
                            if assetItem.isIgnorable():
                                menu.addAction(ToggleIgnoreItemsAction(menu, self.__node, items, not assetItem.isIgnored()))
                            if assetItem.isDeletable():
                                try:
                                    menu.addAction(RemoveItemsAction(menu, self.__node, items))
                                except Exception as exception:
                                    log.exception('Error adding action to context menu: %s' % str(exception))

                            if assetItem.canDuplicate():
                                try:
                                    menu.addAction(DuplicateItemAction(menu, self.__node, items))
                                except:
                                    import traceback
                                    traceback.print_exc()

                            if len(items) == 1:
                                assetItem.addToContextMenu(menu, self.__node)
                menu.exec_(pos)
                for item in items:
                    item.setHiliteColor(None)
                    self.__tree.update(self.__tree.indexFromItem(item))

                event.accept()
        return

    def __listKeyPressCallback(self, event):
        key = event.key()
        try:
            text = str(event.text()).lower()
        except UnicodeEncodeError:
            text = ''

        if event.isAccepted():
            return
        if key == QtCore.Qt.Key_Delete:
            RemoveItemsAction(None, self.__node, self.__tree.selectedItems()).go(True)
        else:
            if text == 'd':
                items = [ x for x in self.__tree.selectedItems() if x.getItemData()['type'] == 'assetTree' and x.getItemData()['assetItem'].isIgnorable()
                        ]
                if not items:
                    return
                ToggleIgnoreItemsAction(None, self.__node, items, not items[0].getItemData()['assetItem'].isIgnored()).go(True)
        return


def _GetPlural(sequence, suffix='s'):
    return (len(sequence) != 1) * suffix


class RemoveItemsAction(QtWidgets.QAction):

    def __init__(self, parent, node, itemList):
        self.__itemList = []
        for item in itemList:
            d = item.getItemData()
            if d['type'] == 'output':
                if d['port'].getName() == 'default':
                    continue
            else:
                if d['type'] == 'assetTree':
                    if not d['assetItem'].isDeletable():
                        continue
            self.__itemList.append(item)

        message = 'Remove Item'
        if len(self.__itemList) > 1:
            message += 's'
        message += '\tDelete'
        QtWidgets.QAction.__init__(self, message, parent)
        self.__node = node
        self.triggered.connect(self.go)

    def go(self, checked):
        if not self.__node:
            return
        if len(self.__itemList) > 1:
            Utils.UndoStack.OpenGroup('Remove %i Item%s from %s' % (len(self.__itemList),
             _GetPlural(self.__itemList),
             self.__node.getName()))
        try:
            for item in self.__itemList:
                itemType = item.getItemData().get('type')
                if itemType == 'output':
                    Utils.UndoStack.OpenGroup('Remove Output "%s" from %s' % (
                     str(item.text(NAME_COLUMN)),
                     self.__node.getName()))
                    try:
                        port = item.getItemData()['port']
                        self.__node.removeOutput(port.getName())
                        self.__node.layoutContents()
                    finally:
                        Utils.UndoStack.CloseGroup()

                elif itemType == 'assetTree':
                    Utils.UndoStack.OpenGroup('Remove %s from %s' % (
                     str(item.text(NAME_COLUMN)),
                     self.__node.getName()))
                    try:
                        assetItem = item.getItemData()['assetItem']
                        keyNode = item.getItemData().get('key')
                        if issubclass(type(keyNode), NodegraphAPI.Node):
                            self.__node.removeNodeFromOutputMerge(keyNode)
                        assetItem.delete()
                        self.__node.layoutContents()
                    finally:
                        Utils.UndoStack.CloseGroup()

        finally:
            if len(self.__itemList) > 1:
                Utils.UndoStack.CloseGroup()
            self.__node = None
            self.__itemList = None

        return


def IsItemATopLevelAsset(item):
    d = item.getItemData()
    if d['type'] == 'asset':
        return True
    if d['type'] == 'assetTree':
        if item.parent().getItemData()['type'] == 'output':
            return True


class DuplicateItemAction(QtWidgets.QAction):

    def __init__(self, parent, node, itemList):
        self.__importatomic = node
        self.__itemList = []
        for item in itemList:
            d = item.getItemData()
            if d['type'] == 'assetTree':
                if not d['assetItem'].isDeletable():
                    continue
            self.__itemList.append(item)

        message = 'Duplicate Item'
        QtWidgets.QAction.__init__(self, message, parent)
        self.triggered.connect(self.go)

    def go(self, checked):
        if not self.__importatomic:
            return
        if not self.__itemList:
            return
        if len(self.__itemList) > 1:
            Utils.UndoStack.OpenGroup('Duplicate %i Item%s from %s' % (
             len(self.__itemList), _GetPlural(self.__itemList),
             self.__importatomic.getName()))
        else:
            item_name = str(self.__itemList[0].text(NAME_COLUMN))
            if item_name.strip() == '':
                item_name = self.__itemList[0].getItemData()['node'].getType()
            Utils.UndoStack.OpenGroup('Duplicate %s from %s' % (item_name,
             self.__importatomic.getName()))
        try:
            imp = self.__importatomic
            for item in self.__itemList:
                itemType = item.getItemData().get('type')
                if itemType == 'assetTree':
                    try:
                        assetItem = item.getItemData()['assetItem']
                        assetNode = item.getItemData()['node']
                        orig_oport = assetNode.getOutputPortByIndex(0)
                        orig_connports = orig_oport.getConnectedPorts()
                        orig_mergeNode = None
                        if orig_connports:
                            orig_mergeNode = orig_connports[0].getNode()
                        if orig_mergeNode:
                            for output_port in imp.getOutputPorts():
                                pname = output_port.getName()
                                if imp.getMergeNodeForOutput(pname) == orig_mergeNode:
                                    newnode = assetItem.duplicateItem()
                                    if newnode:
                                        imp.insertNodeIntoOutputMerge(newnode, pname)
                                    break

                    finally:
                        pass

        finally:
            Utils.UndoStack.CloseGroup()
            self.__importatomic = None
            self.__itemList = None

        return


class ToggleIgnoreItemsAction(QtWidgets.QAction):

    def __init__(self, parent, node, itemList, ignore):
        self.__node = node
        self.__ignore = ignore
        self.__itemList = []
        for item in itemList:
            d = item.getItemData()
            if d['type'] != 'assetTree':
                continue
            assetItem = d['assetItem']
            if not assetItem.isIgnorable():
                continue
            self.__itemList.append(assetItem)

        if ignore:
            message = 'Disable Asset'
        else:
            message = 'Enable Asset'
        if len(self.__itemList) > 1:
            message += 's'
        message += '\tD'
        QtWidgets.QAction.__init__(self, message, parent)
        self.triggered.connect(self.go)

    def go(self, checked):
        if not self.__node:
            return
        if self.__ignore:
            verb = 'Disable'
        else:
            verb = 'Enable'
        Utils.UndoStack.OpenGroup('%s %i Asset%s  from %s' % (verb,
         len(self.__itemList), _GetPlural(self.__itemList),
         self.__node.getName()))
        try:
            for assetItem in self.__itemList:
                try:
                    assetItem.setIgnored(self.__ignore)
                except Exception as exception:
                    log.exception('Error setting disabled state of asset item %s: %s' % (
                     assetItem, str(exception)))

        finally:
            Utils.UndoStack.CloseGroup()
            self.__node = None
            self.__itemList = None

        return


class AssetListViewItem(UI4.Widgets.SortableTreeWidgetItem):

    def __init__(self, *args):
        UI4.Widgets.SortableTreeWidgetItem.__init__(self, *args)
        self.__primarySpref = None
        return

    def setPrimarySpref(self, spref):
        self.__primarySpref = spref

    def getPrimarySpref(self):
        return self.__primarySpref


class LoadDuplicateWarningDialog(QtWidgets.QDialog):

    def __init__(self):
        QtWidgets.QDialog.__init__(self, None)
        self.setWindowTitle('Duplicate Asset Found')
        layout = QtWidgets.QVBoxLayout(self)
        self.__productLabel = QtWidgets.QLabel('', self)
        layout.addWidget(self.__productLabel)
        layout.addSpacing(32)
        layout.addStretch()
        checkboxLayout = QtWidgets.QHBoxLayout(self)
        layout.addItem(checkboxLayout)
        self.__doForAllCheckbox = QtWidgets.QCheckBox('Apply Action To All Remaining Duplicates', self)
        checkboxLayout.addWidget(self.__doForAllCheckbox)
        checkboxLayout.addStretch()
        self.__skipButton = QtWidgets.QPushButton('Skip', self)
        self.__addAnywayButton = QtWidgets.QPushButton('Add Anyway', self)
        self.__cancelButton = QtWidgets.QPushButton('Cancel', self)
        buttonLayout = QtWidgets.QHBoxLayout()
        layout.addItem(buttonLayout)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self.__skipButton)
        buttonLayout.addWidget(self.__addAnywayButton)
        buttonLayout.addWidget(self.__cancelButton)
        self.__cancelButton.clicked.connect(self.reject)
        self.__skipButton.clicked.connect(self.__skipButtonClicked)
        self.__addAnywayButton.clicked.connect(self.__addAnywayButtonClicked)
        self.__result = None
        return

    def setProductLabel(self, product):
        self.__productLabel.setText('<b>%s</b> already exists in this Importatomic.' % product)

    def __skipButtonClicked(self):
        self.__result = 'skip'
        self.accept()

    def __addAnywayButtonClicked(self):
        self.__result = 'add'
        self.accept()

    def getResult(self):
        return (
         self.__result, self.__doForAllCheckbox.isChecked())


class PortEditorWidget(QtWidgets.QWidget):

    def __init__(self, parent, node, portName):
        QtWidgets.QWidget.__init__(self, parent)
        self.__node = node
        self.__portName = portName
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(2, 2, 2, 2)
        self.layout().setSpacing(2)
        self.__label = QtWidgets.QLabel('output', self)
        self.__field = QT4FormWidgets.InputWidgets.InputLineEdit(self)
        self.__field.setText(portName)
        self.layout().addWidget(self.__label)
        self.layout().addWidget(self.__field)
        self.setMinimumHeight(self.__field.height())
        if portName == 'default':
            self.__field.setReadOnly(True)
            return
        if hasattr(self.__field, 'EMITS_CUSTOM_FOCUS_EVENTS') and self.__field.EMITS_CUSTOM_FOCUS_EVENTS:
            self.__field.lostFocus.connect(self.__returnPressedCallback)
        else:
            self.__field.lostFocus.connect(self.__returnPressedCallback)

    def setText(self, name):
        self.__field.setText(name)
        self.__portName = name

    def __returnPressedCallback(self):
        value = str(self.__field.text()).strip()
        if not value:
            self.__field.setText(self.__portName)
            return
        if value == self.__portName:
            return
        self.__node.renameOutputPort(self.__portName, value)


class EditorStatusWidget(QtWidgets.QWidget):
    customNameStateChange = QtCore.pyqtSignal(bool)
    customNameFieldChange = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.__iconLabel = QtWidgets.QLabel('', self)
        self.__iconLabel.setFixedSize(QtCore.QSize(16, 16))
        self.__textLabel = QtWidgets.QLabel('', self)
        self.__inputEdit = QT4FormWidgets.InputWidgets.InputLineEdit(self)
        self.__inputEdit.hide()
        layout.addWidget(self.__iconLabel)
        layout.addWidget(self.__textLabel)
        layout.addWidget(self.__inputEdit, 2)
        layout.addStretch()
        self.__enableCustomName = QtWidgets.QCheckBox('use custom asset name', self)
        self.__enableCustomName.hide()
        self.setFixedHeight(self.__inputEdit.height())
        layout.addWidget(self.__enableCustomName)
        self.__enableCustomName.clicked.connect(self.__enableClicked)
        if hasattr(self.__inputEdit, 'EMITS_CUSTOM_FOCUS_EVENTS') and self.__inputEdit.EMITS_CUSTOM_FOCUS_EVENTS:
            self.__inputEdit.lostFocus.connect(self.__customFieldChanged)
        else:
            self.__inputEdit.lostFocus.connect(self.__customFieldChanged)

    def update(self, text, icon, potentialCustomName=False, activeCustomName=False):
        self.__textLabel.setText(text)
        self.__inputEdit.setText(text)
        if activeCustomName:
            self.__textLabel.setText('')
            self.__inputEdit.setText(text)
            self.__textLabel.hide()
            self.__inputEdit.show()
        else:
            self.__textLabel.setText(text)
            self.__inputEdit.setText('')
            self.__textLabel.show()
            self.__inputEdit.hide()
        if icon:
            self.__iconLabel.setPixmap(icon.pixmap(16, 16))
        else:
            self.__iconLabel.setPixmap(UI4.Util.ScenegraphIconManager.GetPixmap('none'))
        self.__enableCustomName.setChecked(activeCustomName)
        if potentialCustomName:
            self.__enableCustomName.show()
        else:
            self.__enableCustomName.hide()

    def __enableClicked(self):
        self.customNameStateChange.emit(self.__enableCustomName.isChecked())

    def __customFieldChanged(self):
        self.customNameFieldChange.emit(str(self.__inputEdit.text()))