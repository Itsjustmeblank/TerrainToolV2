import maya.api.OpenMaya as om
import maya.cmds as cmds
import math


class TerrainWidget:

    def __init__(self, name="terrain_widget", radius_name="terrain_radius"):
        self.widget_name = name
        self.radius_name = radius_name

    def create(self, radius):
        if cmds.objExists(self.widget_name):
            cmds.select(self.widget_name)
            return

        loc = cmds.spaceLocator(name=self.widget_name)[0]

        cmds.setAttr(loc + ".ty", lock=True, keyable=False, channelBox=False)

        cmds.setAttr(loc + ".localScaleX", 1.5)
        cmds.setAttr(loc + ".localScaleY", 1.5)
        cmds.setAttr(loc + ".localScaleZ", 1.5)

        self.create_radius_visual(radius)

        cmds.select(clear=True)

    def get_position(self):
        if not cmds.objExists(self.widget_name):
            cmds.warning("Create the widget first.")
            return None

        return cmds.xform(self.widget_name, q=True, ws=True, t=True)

    def create_radius_visual(self, radius):
        if cmds.objExists(self.radius_name):
            return

        circle = cmds.circle(
            name=self.radius_name,
            normal=(0, 1, 0),
            radius=1
        )[0]

        cmds.parent(circle, self.widget_name)
        cmds.setAttr(circle + ".translate", 0, 0, 0)

        self.update_radius(radius)

    def update_radius(self, radius):
        if cmds.objExists(self.radius_name):
            cmds.setAttr(self.radius_name + ".scaleX", radius)
            cmds.setAttr(self.radius_name + ".scaleZ", radius)


class TerrainTool:

    def __init__(self):

        self.feature_type = "mountain"

        self.center_x = 0.0
        self.center_z = 0.0

        self.intensity = 3.0
        self.noise_strength = 0.5

        self.original_vertices = {}

        self.widget_name = "terrain_widget"
        self.radius_name = "terrain_radius"

        self.widget = TerrainWidget(self.widget_name, self.radius_name)


    def get_selected_mesh(self):
        sel = om.MGlobal.getActiveSelectionList()

        if sel.length() == 0:
            om.MGlobal.displayError("Select a mesh.")
            return None

        dag = sel.getDagPath(0)

        try:
            dag.extendToShape()
        except:
            om.MGlobal.displayError("Selection has no shape.")
            return None

        if not dag.node().hasFn(om.MFn.kMesh):
            om.MGlobal.displayError("Selected object is not a polygon mesh.")
            return None

        return om.MFnMesh(dag)

    def get_vertices(self, mesh_fn):
        return mesh_fn.getPoints(om.MSpace.kWorld)


    def compute_distance(self, v):
        dx = v.x - self.center_x
        dz = v.z - self.center_z
        return math.sqrt(dx * dx + dz * dz)

    def compute_falloff(self, distance):
        radius = self.radius

        t = distance / radius
        if t >= 1.0:
            return 0.0

        return 1 - (3 * t * t - 2 * t * t * t)

    def sample_noise(self, x, z):
        return math.sin(x * 0.3) * math.cos(z * 0.3)





    def apply_mountain(self, v, dist):
        falloff = self.compute_falloff(dist)

        height = falloff * self.intensity
        height += self.sample_noise(v.x, v.z) * self.noise_strength * falloff

        return v.y + height

    def apply_valley(self, v, dist):
        falloff = self.compute_falloff(dist)

        depth = falloff * self.intensity
        depth += self.sample_noise(v.x, v.z) * self.noise_strength * falloff

        return v.y - depth

    def apply_feature(self, v, dist):
        if self.feature_type == "mountain":
            return self.apply_mountain(v, dist)
        elif self.feature_type == "valley":
            return self.apply_valley(v, dist)
        return v.y






    def modify_vertices(self, vertices):
        new_verts = []

        for v in vertices:
            dist = self.compute_distance(v)

            new_v = om.MPoint(v)

            if dist <= self.radius:
                new_v.y = self.apply_feature(v, dist)

            new_verts.append(new_v)

        return new_verts

    def update_mesh(self, mesh_fn, vertices):
        mesh_fn.setPoints(vertices, om.MSpace.kWorld)





    def run(self):

        if not cmds.objExists(self.widget.widget_name):
            cmds.warning("Create the widget first.")
            return

        mesh_fn = self.get_selected_mesh()
        if not mesh_fn:
            return

        pos = self.widget.get_position()
        if not pos:
            return

        self.center_x = pos[0]
        self.center_z = pos[2]


        self.radius = cmds.getAttr(self.widget.radius_name + ".scaleX")

        self.widget.update_radius(self.radius)

        verts = self.get_vertices(mesh_fn)
        mesh_name = mesh_fn.name()

        if mesh_name not in self.original_vertices:
            self.original_vertices[mesh_name] = [om.MPoint(v) for v in verts]

        new_verts = self.modify_vertices(verts)
        self.update_mesh(mesh_fn, new_verts)

        om.MGlobal.displayInfo("Terrain applied")





    def reset(self):

        mesh_fn = self.get_selected_mesh()
        if not mesh_fn:
            return

        mesh_name = mesh_fn.name()

        if mesh_name not in self.original_vertices:
            return

        mesh_fn.setPoints(self.original_vertices[mesh_name], om.MSpace.kWorld)

        om.MGlobal.displayInfo("Terrain reset")






    def enable_live_update(self):

        if not cmds.objExists(self.widget.widget_name):
            cmds.warning("Create widget first.")
            return

        def callback():
            self.run()

        for axis in ["translateX", "translateY", "translateZ"]:
            cmds.scriptJob(
                attributeChange=[f"{self.widget.widget_name}.{axis}", callback],
                protected=True
            )




tool = TerrainTool()

def apply_mountain():
    tool.feature_type = "mountain"
    tool.run()


def apply_valley():
    tool.feature_type = "valley"
    tool.run()


def reset_terrain():
    tool.reset()


def enable_live():
    tool.enable_live_update()


def create_widget():
    tool.widget.create(tool.intensity)
    