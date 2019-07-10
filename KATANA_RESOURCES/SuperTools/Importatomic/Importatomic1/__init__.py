import logging
from Katana import ResourceFiles, Utils, Plugins

log = logging.getLogger('Importatomic.HandlerRegistry')


def InitializeImportatomicPlugins():
    try:
        from Katana import QtWidgets
        guiMode = not QtWidgets.QApplication.startingUp() and isinstance(QtWidgets.QApplication.instance(), QtWidgets.QApplication)
    except ImportError:
        guiMode = False

    if not hasattr(Plugins, 'ImportatomicAPI'):
        import ImportatomicAPI
        Plugins.ImportatomicAPI = ImportatomicAPI

    searchPath = ResourceFiles.GetSearchPaths('Importatomic')

    plugins = Utils.Plugins.Load('ImportatomicModule', None, searchPath)

    for plugin in plugins:
        log.info("%s v%s" % (plugin.name.ljust(34, "-"), plugin.apinum))
        # data refers to the "Register" function of the sub-importatomic plugin
        try:
            data = plugin.data
            if isinstance(data, tuple):
                if len(data) == 2:
                    if guiMode:
                        data[0]()
                        if data[1] is not None:
                            data[1]()
                    else:
                        data[0]()
            else:
                if guiMode:
                    data()
        except Exception as e:
            log.warning("ImportatomicPlugin Error For '%s' %s" % (plugin.name, e), exc_info=True)


InitializeImportatomicPlugins()