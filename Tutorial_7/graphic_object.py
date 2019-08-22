import numpy as np
from gl_lib.transmat import normalized

class PhongShading:

    def __init__(self):
        self.color = np.ones(3, np.float32)

        self.ambientCoef = 0.1
        self.specularCoef = 0.6
        self.phongP = 256

        self.reflectionStrength = 0.7

    def shade(self, normal, lightDir, viewDir, lightColor):
        ambient = np.ones(3, np.float32) * self.ambientCoef
        diffuse = max(0.0, normal @ lightDir) * lightColor
        reflectDir = -lightDir + 2.0 * (normal @ lightDir) * normal
        specular = pow(max(0.0, viewDir @ reflectDir),
                       self.phongP) * self.specularCoef * lightColor

        shadeColor = (ambient + diffuse + specular) * self.color
        return shadeColor

class Ray:

    def __init__(self, origin=np.zeros(3, np.float), dir=np.zeros(3, np.float)):
        self.origin = origin
        self.dir = dir


    def get_pos(self, t):
        return self.origin + t * self.dir


class Sphere:

    def __init__(self, origin, radius):
        self.origin = origin
        self.radius = radius
        self.shadeParam = PhongShading()

    def intersect(self, ray):
        a = ray.dir @ ray.dir
        b = 2.0 * (ray.origin @ ray.dir - self.origin @ ray.dir)
        c = self.origin @ self.origin + ray.origin @ ray.origin - 2.0 * ray.origin @ self.origin - self.radius**2

        delta = b**2 - 4.0 * a * c
        if delta >= 1.0e-3:
            s = (-b - np.sqrt(delta))/(2.0 * a)
            if s > 1.0e-3:
                return s

        return -1.0

    def normal(self, pos):
        return normalized(pos - self.origin)


class Triangle:

    def __init__(self, p1, p2, p3):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.normalVec = normalized(np.cross(p2 - p1, p3 - p1))

        self.mat = np.zeros((3, 3), np.float)
        self.mat[:, 0] = p2 - p1
        self.mat[:, 1] = p3 - p1
        self.mat[:, 2] = self.normalVec

        self.invMat = np.linalg.inv(self.mat)

        self.shadeParam = PhongShading()

    def intersect(self, ray):
        s = (self.p1 @ self.normalVec - ray.origin @ self.normalVec) / ray.dir @ self.normalVec
        pos = ray.get_pos(s)

        para = self.invMat @ (pos - self.p1)
        if para[0] >= 0.0 and para[1] >= 0.0 and para[0] + para[1] <= 1.0:
            return s

        return -1.0

    def normal(self, pos):
        return self.normalVec
