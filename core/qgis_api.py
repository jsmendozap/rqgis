from qgis.PyQt.QtCore import QObject, pyqtSlot
from qgis.core import QgsProject, QgsVectorFileWriter, QgsUnitTypes
import tempfile
import os

class QGISApi(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    @pyqtSlot('PyQt_PyObject', result='PyQt_PyObject')
    def dispatch(self, msg):
        method = msg.get('method')
        match method:
            case "list_layers":
                self.result = self.list_layers(msg.get("args", {}))
            case "get_layer":
                self.result = self.get_layer(msg.get("args", {}))
            case "project_state":
                self.result = self.project_state()
            case _:
                self.result = {"type": "response", "error": f"Unknown method: {method}"}
        
        return self.result
    
    @pyqtSlot(result='PyQt_PyObject')
    def project_state(self):
        project = QgsProject.instance()
        self.result = {
            "type": "response",
            "title": project.title(),
            "path": project.homePath(),
            "crs": project.crs().authid(),
            "units": QgsUnitTypes.toString(project.crs().mapUnits()),
            "layers": [layer.name() for layer in project.mapLayers().values()]
        }
        return self.result

    def list_layers(self, args):
        print(args)
        type = args.get("type")
        
        if type is not None:
            type = int(type)

        layers = QgsProject.instance().mapLayers().values()
        return {
            "type": "response",
            "layers": [{"name": l.name(), "id": l.id(), "type": l.type()} 
                       for l in layers 
                       if type is None or l.type() == type]
        }

    def get_layer(self, args):
        pass
        """
        name = args.get("name")
        layers = QgsProject.instance().mapLayersByName(name)
        if not layers:
            return {"type": "response", "error": f"Layer not found: {name}"}
        path = os.path.join(tempfile.gettempdir(), f"{name}.fgb")
        QgsVectorFileWriter.writeAsVectorFormat(layers[0], path)
        return {"type": "response", "path": path}
        """
        