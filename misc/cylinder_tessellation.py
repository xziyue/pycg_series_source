import numpy as np


def _circle_pos(theta):
    theta = np.asarray(theta)
    x = np.cos(theta)
    y = np.zeros(theta.size, np.float)
    z = np.sin(theta)
    return np.stack([x, y, z], axis=1)


class _Triangle:

    def __init__(self, vertices = None, genNormal = False):
        if vertices is None:
            self.vertices = np.asarray([np.asarray([0, 0, 1], np.float) for _ in range(3)])
        else:
            self.vertices = vertices

        # normals for rendering
        self.normals = None

        if genNormal:
            self.generate_normal()

    def generate_normal(self):
        self.normals = np.copy(self.vertices)
        self.normals[:, 1].fill(0.0)
        norms = np.linalg.norm(self.normals, axis=1)
        for i in range(3):
            self.normals[i, :] /= norms[i]


def uniform_tessellate_half_cylinder(hStep = 12, vStep = 12):
    assert hStep > 1 and vStep > 1

    thetaTicks = np.linspace(0.0, np.pi, hStep)
    vTicks = np.linspace(0.0, 1.0, vStep)

    hPos = _circle_pos(thetaTicks)

    cylinderGrid = []

    for i in range(vStep):
        gridPos = hPos + np.asarray([0.0, vTicks[i], 0.0])
        cylinderGrid.append(gridPos)

    cylinderGrid = np.asarray(cylinderGrid)

    triVertexIndex1 = ([0, 2, 1], ...)
    triVertexIndex2 = ([1, 2, 3], ...)

    triangles = []

    # create triangles
    for i in range(vStep - 1):
        for j in range(hStep - 1):
            vertexIndices = (
                [i, i, i + 1, i + 1],
                [j, j + 1, j, j + 1]
            )
            vertices = cylinderGrid[vertexIndices]

            triangle1 = _Triangle(vertices[triVertexIndex1], True)
            triangle2 = _Triangle(vertices[triVertexIndex2], True)
            triangles.append(triangle1)
            triangles.append(triangle2)

    return triangles





