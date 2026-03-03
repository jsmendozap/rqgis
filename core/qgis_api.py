from qgis.PyQt.QtCore import QObject, pyqtSlot
from qgis.core import QgsProject, QgsUnitTypes, QgsMapLayer, QgsRasterLayer, QgsVectorLayer
import processing
import tempfile
import os

class QGISApi(QObject):
    def __init__(self):
        super().__init__()
        self.result = None
        self.needs_update = False
        self._temp_files = []

    @pyqtSlot('PyQt_PyObject', result='PyQt_PyObject')
    def dispatch(self, msg):
        method = msg.get('method')
        match method:
            case "list_layers":
                self.result = self.list_layers(msg.get("args", {}))
            case "get_layer":
                self.result = self.get_layer(msg.get("args", {}))
            case "insert_layer":
                self.result = self.insert_layer(msg.get("args", {}))
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
            "units": QgsUnitTypes.toString(project.crs().mapUnits())
        }
        return self.result

    def list_layers(self, args):
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
        column = args.get("col")
        field = args.get("value")
        
        if column == "name":
            layer = QgsProject.instance().mapLayersByName(field)
        elif column == "id":
            layer = QgsProject.instance().mapLayer(field)
        else: 
            result = {"type": "error", "error": f"Unknown layer: {column}"}
            return result
        
        if not layer:
            return {"type": "error", "error": f"Layer not found: {field}"}

        type = layer[0].type()
        if type == QgsMapLayer.VectorLayer:
            fd, path = tempfile.mkstemp(suffix=".fgb")
            os.close(fd)
            processing.run("native:savefeatures", {'INPUT': layer[0], 'OUTPUT': path})
        elif type == QgsMapLayer.RasterLayer:
            print("entró")
            fd, path = tempfile.mkstemp(suffix=".tif")
            os.close(fd)
            processing.run("gdal:translate", {'INPUT': layer[0], 'OUTPUT': path, 'OPTIONS': ''})
        else:
            return {"type": "error", "error": f"Unsupported layer type: {type}"}

        return {"type": "response", "path": path}
    
    def insert_layer(self, args):
        path = args.get("path")
        if not os.path.exists(path):
            return {"type": "error", "error": f"Layer not found: {path}"}
        
        name = args.get("name")
        if not name:
            name = os.path.splitext(os.path.basename(path))[0]

        existing = QgsProject.instance().mapLayersByName(name)
        if existing:
            name = f"{name}_{len(existing)}"

        ext = os.path.splitext(path)[1].lower()
        if ext == ".tif":
            layer = QgsRasterLayer(path, name)
        else:
            layer = QgsVectorLayer(path, name, "ogr")

        if not layer.isValid():
            return {"type": "error", "error": f"Invalid layer: {path}"}
        
        QgsProject.instance().addMapLayer(layer)
        self._temp_files.append(path)
        return {"type": "response", "id": layer.id()}
    
    def update_state(self):
        self.needs_update = True

    @pyqtSlot(result='PyQt_PyObject')
    def check_update(self):
        if not self.needs_update:
            self.result = None
            return None
        self._needs_update = False
        return self.project_state()
    
    def remove_temp_files(self):
        for path in self._temp_files:
            print(path)
            if os.path.exists(path):
                os.remove(path)
        self._temp_files = []