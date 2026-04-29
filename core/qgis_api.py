from qgis.PyQt.QtCore import QObject, pyqtSlot, QEventLoop, Qt
from qgis.gui import QgsMapToolExtent, QgsMapToolEmitPoint
from qgis.core import (
    QgsProject, QgsUnitTypes, QgsMapLayer, QgsRasterLayer,
    QgsVectorLayer, QgsWkbTypes, QgsProcessingFeatureSourceDefinition
)
from ..ui.user_interaction import QuestionDialog
import processing
import uuid
import tempfile
import os

class QGISApi(QObject):
    """
    Exposes QGIS functionalities to be called from the R process.

    This class acts as a server, receiving requests via the `dispatch` slot,
    executing the corresponding QGIS action, and returning the result.
    It handles layer operations, project state, and temporary file management.
    """
    def __init__(self, iface):
        """
        Initializes the QGISApi.

        Args:
            iface: The QgisInterface instance.
        """
        super().__init__()
        self.result = None
        self.needs_update = False
        self._temp_files = []
        self.iface = iface

    @pyqtSlot('PyQt_PyObject', result='PyQt_PyObject')
    def dispatch(self, msg):
        """
        Main entry point for requests from R.

        Parses the request message and routes it to the appropriate handler method.

        Args:
            msg (dict): A dictionary containing 'method' and 'args' for the request.

        Returns:
            dict: A dictionary with the response to be sent back to R.
        """
        method = msg.get('method')
        match method:
            case "list_layers":
                self.result = self.list_layers(msg.get("args", {}))
            case "get_layer":
                self.result = self.get_layer(msg.get("args", {}))
            case "insert_layer":
                self.result = self.insert_layer(msg.get("args", {}))
            case "layer_info":
                self.result = self.get_layer_info(msg.get("args", {}))
            case "project_state":
                self.result = self.project_state()
            case "canvas_extent":
                self.result = self.get_canvas_extent()
            case "selected_features":
                self.result = self.get_selected_features()
            case "draw_bbox":
                self.result = self.draw_bbox()
            case "draw_points":
                self.result = self.draw_points(msg.get("args", {}))
            case "question":
                self.result = self.question(msg.get("args", {}))
            case _:
                self.result = {"type": "error", "error": f"Unknown method: {method}"}
        
        return self.result
    
    @pyqtSlot(result='PyQt_PyObject')
    def project_state(self):
        """
        Retrieves the current state of the QGIS project.

        Returns:
            dict: A dictionary with project title, path, CRS, and map units.
        """
        project = QgsProject.instance()
        result = {
            "type": "response",
            "title": project.title(),
            "path": project.homePath(),
            "crs": project.crs().userFriendlyIdentifier(),
            "units": QgsUnitTypes.toString(project.crs().mapUnits())
        }
        return result

    def list_layers(self, args):
        """
        Lists layers in the current QGIS project.

        Args:
            args (dict): A dictionary that may contain a 'type' filter
                         (0 for vector, 1 for raster).

        Returns:
            dict: A response containing a list of layers (name, id, type).
        """
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
        """
        Exports a QGIS layer to a temporary file.

        The layer is identified by its name or ID. Vector layers are saved as
        FlatGeobuf (.fgb) and rasters as GeoTIFF (.tif).

        Args:
            args (dict): A dictionary with 'col' ('name' or 'id') and 'value'.

        Returns:
            dict: A response containing the path to the temporary file or an error.
        """
        
        layer = self._resolve_layer(args)
        if isinstance(layer, dict):
            return layer
        
        if layer.providerType() in ("wms", "bing", "xyz"):
            return {"type": "error", "error": "Layer is a base map and cannot be exported"}

        type = layer.type()
        if type == QgsMapLayer.VectorLayer:
            path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.fgb")
            try: 
                processing.run("native:savefeatures", {'INPUT': layer, 'OUTPUT': path})
            except Exception as e: 
                return {"type": "error", "error": f"Failed to save layer: {e}"}
        elif type == QgsMapLayer.RasterLayer:
            path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.tif")
            try: 
                processing.run("gdal:translate", {'INPUT': layer, 'OUTPUT': path, 'OPTIONS': ''})
            except Exception as e: 
                return {"type": "error", "error": f"Failed to save layer: {e}"}
        else:
            return {"type": "error", "error": f"Unsupported layer type: {type}"}

        self.add_temp_file(path)
        return {"type": "response", "path": path}
    
    def insert_layer(self, args):
        """
        Inserts a spatial file into QGIS as a new layer.

        Args:
            args (dict): A dictionary with 'path' to the file and an optional 'name'.

        Returns:
            dict: A response containing the new layer's ID or an error.
        """
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
        self.add_temp_file(path)
        return {"type": "response", "id": layer.id()}
    
    def get_canvas_extent(self):
        """
        Gets the extent of the current map canvas view.

        Returns:
            dict: A response with the extent as a WKT polygon and its CRS.
        """
        response = {
            "type": "response",
            "wkt": self.iface.mapCanvas().extent().asWktPolygon(), 
            "crs": self.iface.mapCanvas().mapSettings().destinationCrs().authid()
            }
        return response

    def get_selected_features(self):
        """
        Exports selected features from the active vector layer.

        Returns:
            dict: A response containing the path to a temporary file with the
                  selected features, or an error.
        """
        layer = self.iface.activeLayer()
        
        if layer is None:
            return {"type": "error", "error": "No active layer"}
        
        if not hasattr(layer, 'selectedFeatureCount'):
            return {"type": "error", "error": "Active layer is not a vector layer"}
        
        if layer.selectedFeatureCount() == 0:
            return {"type": "error", "error": "No features selected"}

        path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.fgb")
        try:        
            processing.run("native:savefeatures", {
                'INPUT': QgsProcessingFeatureSourceDefinition(layer.id(), selectedFeaturesOnly=True),
                'OUTPUT': path
            })
        except Exception as e:
            return {"type": "error", "error": f"Failed to save features: {e}"}
        
        self.add_temp_file(path)

        return {"type": "response", "path": path}

    @pyqtSlot(result='PyQt_PyObject')
    def get_layer_info(self, args):
        """
        Retrieves detailed metadata for a specific layer.

        Args:
            args (dict): A dictionary with 'column' ('name' or 'id') and 'value'.

        Returns:
            dict: A response with detailed layer information or an error.
        """
        
        layer = self._resolve_layer(args)
        if isinstance(layer, dict):
            return layer
        
        info = {
            "type": "response",
            "name": layer.name(),
            "crs": layer.crs().authid(),
            "units": QgsUnitTypes.toString(layer.crs().mapUnits()),
            "extent": {
                "xmin": layer.extent().xMinimum(),
                "xmax": layer.extent().xMaximum(),
                "ymin": layer.extent().yMinimum(),
                "ymax": layer.extent().yMaximum(),
            }
        }

        type = layer.type()
        if type == QgsMapLayer.VectorLayer:
            info["layer_type"] = "vector"
            info["geometry"] = QgsWkbTypes.displayString(layer.wkbType())
            info["features"] = layer.featureCount()
            info["fields"] = [f.name() for f in layer.fields()]

        elif type == QgsMapLayer.RasterLayer:
            info["layer_type"] = "raster"
            info["bands"] = layer.bandCount()
            info["width"] = layer.width()
            info["height"] = layer.height()
            info["res_x"] = layer.rasterUnitsPerPixelX()
            info["res_y"] = layer.rasterUnitsPerPixelY()

        return info

    def draw_bbox(self):
        """
        Activates an interactive map tool for the user to draw a bounding box.
        Blocks the local execution loop until drawn or cancelled.
        """
        canvas = self.iface.mapCanvas()
        prev_tool = canvas.mapTool()
        tool = QgsMapToolExtent(canvas)
        loop = QEventLoop()
        result = {}

        def on_extent(extent):
            result["extent"] = extent
            loop.quit()

        def on_tool_changed(new_tool):
            if new_tool != tool:
                loop.quit()

        tool.extentChanged.connect(on_extent)
        canvas.mapToolSet.connect(on_tool_changed)
        canvas.setMapTool(tool)
        loop.exec()

        tool.extentChanged.disconnect(on_extent)
        try:
            canvas.mapToolSet.disconnect(on_tool_changed)
        except TypeError:
            pass

        if canvas.mapTool() == tool:
            canvas.setMapTool(prev_tool)

        extent = result.get("extent")
        if extent is None:
            return {"type": "error", "error": "Operation cancelled"}

        crs = canvas.mapSettings().destinationCrs().authid()
        return {
            "type": "response",
            "data": {
                "xmin": extent.xMinimum(),
                "xmax": extent.xMaximum(),
                "ymin": extent.yMinimum(),
                "ymax": extent.yMaximum(),
                "crs": crs
            }
        }

    def draw_points(self, args):
        """
        Activates an interactive map tool for the user to draw n points.
        Blocks the local execution loop until drawn or cancelled.
        """
        n = args.get("n", 1)
        canvas = self.iface.mapCanvas()
        prev_tool = canvas.mapTool()
        loop = QEventLoop()
        result = {"points": [], "cancelled": False}

        tool = QgsMapToolEmitPoint(canvas)

        def on_clicked(point, button):
            if button == Qt.LeftButton:
                result["points"].append({"x": point.x(), "y": point.y()})
                if len(result["points"]) >= n:
                    loop.quit()

        def on_tool_changed(new_tool):
            if new_tool != tool:
                result["cancelled"] = True
                loop.quit()

        tool.canvasClicked.connect(on_clicked)
        canvas.mapToolSet.connect(on_tool_changed)
        canvas.setMapTool(tool)
        
        loop.exec()

        tool.canvasClicked.disconnect(on_clicked)
        try:
            canvas.mapToolSet.disconnect(on_tool_changed)
        except TypeError:
            pass

        if canvas.mapTool() == tool:
            canvas.setMapTool(prev_tool)

        if result["cancelled"] or len(result["points"]) < n:
            return {"type": "error", "error": "Operation cancelled"}

        crs = canvas.mapSettings().destinationCrs().authid()
        
        response = {
            "type": "response",
            "data": {
                "points": result["points"],
                "crs": crs
            }
        }
        
        return response

    def update_state(self):
        """Flags that the project state has changed and needs to be sent to R."""
        self.needs_update = True

    @pyqtSlot(result='PyQt_PyObject')
    def check_update(self):
        """
        Checks if a project update is pending and, if so, dispatches it.
        This is called synchronously from the R bridge before running code.
        """
        if not self.needs_update:
            self.result = None
            return None
        self.needs_update = False
        self.dispatch({"method": "project_state", "args": None})
    
    def remove_temp_files(self):
        """Removes all temporary files created during the session."""
        for path in self._temp_files:
            if os.path.exists(path):
                os.remove(path)
        self._temp_files = []

    def add_temp_file(self, path):
        self._temp_files.append(path)

    def question(self, msg):
        method = msg.get("method")
        args = msg.get("args")

        result = QuestionDialog(self.iface.mainWindow(), method, args)
        return result.dispatch()
    
    def _resolve_layer(self, args):
        """Returns QgsMapLayer or an error dict."""
        col = args.get("col")
        value = args.get("value")

        if col == "name":
            layers = QgsProject.instance().mapLayersByName(value)
            if not layers:
                return {"type": "error", "error": f"Layer not found: {value}"}
            return layers[0]
        if col == "id":
            layer = QgsProject.instance().mapLayer(value)
            if layer is None:
                return {"type": "error", "error": f"Layer not found: {value}"}
            return layer
        
        return {"type": "error", "error": f"Unknown column: {col}"}
