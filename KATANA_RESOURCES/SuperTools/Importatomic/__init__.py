import logging
from Katana import QtWidgets
from Importatomic1 import ImportatomicAPI
from Importatomic1 import Node
from Importatomic1.Constants import IMPORTATOMIC_VERSION

# Get Logger
log = logging.getLogger('Importatomic.NodeRegistry')
log.info("Registering Importatomic SuperTool Node ----- v%s" % IMPORTATOMIC_VERSION)

importatomic_editor_class = ImportatomicAPI.GetImportatomicEditorClass if QtWidgets.QApplication.instance() else None

PluginRegistry = [('SuperTool', 2, 'Importatomic', (Node.ImportatomicNode, importatomic_editor_class))]

log.info("Finished Registering Importatomic Plugin")

# Use the following to find the plugin in the registry
# plugins = [y for x in Utils.Plugins.CachedModulePaths.values() for y in x]
# importatomic_plugin = Utils.Plugins.Search(plugins, "Importatomic")
# reload(importatomic_plugin.module)