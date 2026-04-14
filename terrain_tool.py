import math
import maya.cmds as cmds

from PySide2 import QtWidgets, QtCore
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui



def maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


class TerrainTool:

    def __init__(self):

        self.mesh = None
        self.mode = "mountain"
        self.intensity = 10.0
        self.radius = 0.3

        self.noise_enabled = True
        self.noise_strength = 0.2

        self.original_verts = {}

    def get_mesh(self):
        sel = cmds.ls(sl=True, long=True)
        return sel[0] if sel else None

    def cache_original(self, mesh):

        if mesh in self.original_verts:
            return

        verts = cmds.ls(mesh + ".vtx[*]", fl=True)

        self.original_verts[mesh] = [
            cmds.pointPosition(v, w=True) for v in verts
        ]

    def noise(self, x, z):
        n = math.sin(x * 12.9898 + z * 78.233) * 43758.5453
        return (n - math.floor(n)) * 2.0 - 1.0

    def generate(self):

        self.mesh = self.get_mesh()
        if not self.mesh:
            cmds.warning("Select a mesh")
            return

        self.cache_original(self.mesh)

        verts = cmds.ls(self.mesh + ".vtx[*]", fl=True)

        bb = cmds.exactWorldBoundingBox(self.mesh)

        cx = (bb[0] + bb[3]) * 0.5
        cz = (bb[2] + bb[5]) * 0.5

        width = bb[3] - bb[0]
        depth = bb[5] - bb[2]

        scaled_radius = self.radius * max(width, depth)

        for v in verts:

            pos = cmds.pointPosition(v, w=True)

            dx = pos[0] - cx
            dz = pos[2] - cz

            dist = math.sqrt(dx * dx + dz * dz)

            if dist > scaled_radius:
                continue

            t = 1.0 - (dist / scaled_radius)
            falloff = t * t * (3.0 - 2.0 * t)

            offset = falloff * self.intensity

            if self.noise_enabled:

                main_noise = self.noise(pos[0], pos[2]) * self.noise_strength
                micro_noise = self.noise(pos[0] * 3.0, pos[2] * 3.0) * (self.noise_strength * 0.3)

                offset += (main_noise * falloff) + micro_noise

            if self.mode == "valley":
                offset *= -1

            cmds.move(0, offset, 0, v, r=True, os=True)

    def reset(self):

        mesh = self.get_mesh()

        if not mesh or mesh not in self.original_verts:
            cmds.warning("Nothing to reset")
            return

        verts = cmds.ls(mesh + ".vtx[*]", fl=True)
        original = self.original_verts[mesh]

        for i, v in enumerate(verts):
            cmds.move(
                original[i][0],
                original[i][1],
                original[i][2],
                v,
                absolute=True,
                worldSpace=True
            )




class TerrainUI(QtWidgets.QDialog):

    def __init__(self, parent=None):

        super(TerrainUI, self).__init__(parent or maya_main_window())

        self.setWindowTitle("Terrain Tool")

        self.tool = TerrainTool()

        self.build_ui()
        self.build_layout()
        self.build_connections()

    def build_ui(self):

        self.mode_label = QtWidgets.QLabel("Mode")
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(["Mountain", "Valley"])

        self.intensity_label = QtWidgets.QLabel("Intensity")
        self.intensity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.intensity.setRange(1, 100)
        self.intensity.setValue(20)

        self.radius_label = QtWidgets.QLabel("Radius (Mesh %)")
        self.radius = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.radius.setRange(1, 100)
        self.radius.setValue(30)

        self.noise_label = QtWidgets.QLabel("Noise Strength")
        self.noise_toggle = QtWidgets.QCheckBox("Enable Noise")
        self.noise_toggle.setChecked(True)

        self.noise = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.noise.setRange(0, 100)
        self.noise.setValue(20)

        self.btn_generate = QtWidgets.QPushButton("Generate Terrain")
        self.btn_reset = QtWidgets.QPushButton("Reset Mesh")
        self.btn_close = QtWidgets.QPushButton("Close Tool")

    def build_layout(self):

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self.mode_label)
        layout.addWidget(self.mode)

        layout.addWidget(self.intensity_label)
        layout.addWidget(self.intensity)

        layout.addWidget(self.radius_label)
        layout.addWidget(self.radius)

        layout.addWidget(self.noise_toggle)
        layout.addWidget(self.noise_label)
        layout.addWidget(self.noise)

        layout.addWidget(self.btn_generate)
        layout.addWidget(self.btn_reset)
        layout.addWidget(self.btn_close)

    def build_connections(self):

        self.btn_generate.clicked.connect(self.on_generate)
        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_close.clicked.connect(self.close)

    def on_generate(self):

        self.tool.mode = self.mode.currentText().lower()
        self.tool.intensity = self.intensity.value() / 5.0
        self.tool.radius = self.radius.value() / 100.0

        self.tool.noise_enabled = self.noise_toggle.isChecked()
        self.tool.noise_strength = self.noise.value() / 100.0

        self.tool.generate()

    def on_reset(self):
        self.tool.reset()


_ui = None


def show_ui():

    global _ui

    if _ui:
        try:
            _ui.close()
            _ui.deleteLater()
        except:
            pass

    _ui = TerrainUI()
    _ui.show()