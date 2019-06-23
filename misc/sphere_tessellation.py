import numpy as np


def _sphere_pos(theta, phi):
    xs = np.sin(theta) * np.cos(phi)
    ys = np.sin(theta) * np.sin(phi)
    zs = np.cos(theta)

    return np.stack([xs, ys, zs], axis=2)

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
        norms = np.linalg.norm(self.vertices, axis=1)
        self.normals = self.vertices
        for i in range(3):
            self.normals[i, :] /= norms[i]


def uniform_tessellate_half_sphere(thetaStep = 15, phiStep = 30):
    assert thetaStep > 1 and phiStep > 1

    thetaTicks = np.linspace(np.pi / 2.0, 0, thetaStep)
    phiTicks = np.linspace(0, 2.0 * np.pi, phiStep)

    tv, pv = np.meshgrid(thetaTicks, phiTicks, indexing='ij')
    sphereGrid = _sphere_pos(tv, pv)

    triVertexIndex1 = ([0, 2, 1], ...)
    triVertexIndex2 = ([1, 2, 3], ...)

    triangles = []

    # create triangles
    for i in range(thetaStep - 1):
        for j in range(phiStep - 1):
            vertexIndices = (
                [i, i, i + 1, i + 1],
                [j, j + 1, j, j + 1]
            )
            vertices = sphereGrid[vertexIndices]

            triangle1 = _Triangle(vertices[triVertexIndex1], True)
            triangle2 = _Triangle(vertices[triVertexIndex2], True)
            triangles.append(triangle1)
            triangles.append(triangle2)

    return triangles





