from Tutorial_7.graphic_object import *
import matplotlib.pyplot as plt
from queue import Queue
from multiprocessing import Pool
from functools import partial

class RayTracingConfig:

    def __init__(self):
        self.imageShape = None
        self.pixelSize = 0.0003

        self.cameraOrigin = None
        self.cameraUp = None
        self.cameraFront = None
        self.cameraFocalLength = None

        self.lightPos = None
        self.lightColor = None

        self.strengthThreshold = 0.01

        self.maxRecursion = 4

    def get_screen_pos(self, i, j):
        cameraRight = normalized(np.cross(self.cameraFront, self.cameraUp))
        screenPoint = self.cameraOrigin + self.cameraFocalLength * self.cameraFront

        unitDown = -self.pixelSize * self.cameraUp
        unitRight = self.pixelSize * cameraRight

        topLeft = screenPoint - (self.imageShape[0] / 2) * unitDown - (self.imageShape[1] / 2) * unitRight

        return topLeft + (i + 0.5) * unitDown + (j + 0.5) * unitRight

def ray_trace(config, objects, pxIndLst):
    rayQueue = Queue()

    for pxInd in pxIndLst:
        screenPos = config.get_screen_pos(pxInd[0], pxInd[1])
        ray = Ray(config.cameraOrigin, normalized(screenPos - config.cameraOrigin))
        rayQueue.put((ray, pxInd, 1.0, 1))

    result = np.zeros([config.imageShape[0], config.imageShape[1], 3], np.float32)

    while not rayQueue.empty():
        ray, pxInd, strength, depth = rayQueue.get()
        if strength < config.strengthThreshold:
            continue

        minEyeDistance = 1.0e100
        minDistObject = None
        minDistS = 0.0

        for obj in objects:
            s = obj.intersect(ray)

            if s > 0.0:
                pos = ray.get_pos(s)

                eyeDist = np.linalg.norm(config.cameraOrigin - pos)
                if eyeDist < minEyeDistance:
                    minEyeDistance = eyeDist
                    minDistObject = obj
                    minDistS = s

        if minDistObject is not None:
            # do shadow ray intersection test
            pos = ray.get_pos(minDistS)
            lightDir = normalized(config.lightPos - pos)
            backOrigin = ray.get_pos(minDistS - 1.0e-3)
            backRay = Ray(backOrigin, lightDir)

            noBackIntersection = True
            for obj in objects:
                s = obj.intersect(backRay)
                if s > 0.0:
                    noBackIntersection = False
                    break


            if noBackIntersection:
                obj = minDistObject
                normal = minDistObject.normal(pos)
                viewDir = normalized(config.cameraOrigin - pos)

                # apply shading
                shadeColor = obj.shadeParam.shade(normal, lightDir, viewDir, config.lightColor)
                result[pxInd[0], pxInd[1], :] += shadeColor

                # compute reflection direction
                reflectDir = -lightDir + 2.0 * (normal @ lightDir) * normal
                # create new reflection ray
                newStrength = strength * obj.shadeParam.reflectionStrength
                # create a little bit of offset to avoid self intersection
                rayQueue.put((Ray(backOrigin, reflectDir), pxInd, newStrength, depth + 1))


    return result


config = RayTracingConfig()
config.imageShape = (600, 800)
config.cameraOrigin = np.asarray([0.0, 0.0, 4.0])
config.cameraUp = np.asarray([0.0, 1.0, 0.0])
config.cameraFront = np.asarray([0.0, 0.0, -1.0])
config.cameraFocalLength = 0.1
config.lightColor = np.asarray([1.0, 1.0, 1.0], np.float32)
config.lightPos = np.asarray([0.0, 0.0, 10.0])


sphere1 = Sphere(np.asarray([-2.0, 0.0, 0.0], np.float), 1.0)
sphere1.shadeParam.color = np.asarray([0.3, 0.8, 0.4], np.float32)
sphere2 = Sphere(np.asarray([2.0, 0.0, 0.0], np.float), 1.0)
sphere2.shadeParam.color = np.asarray([0.8, 0.3, 0.4], np.float32)

p1 = np.asarray([-16.0, 16.0, -2.0])
p2 = np.asarray([-16.0, -16.0, -2.0])
p3 = np.asarray([16.0, -16.0, -2.0])
p4 = np.asarray([16.0, 16.0, -2.0])
tri1 = Triangle(p1, p2, p3)
tri1.shadeParam.reflectionStrength = 0.3
tri1.shadeParam.color = np.asarray([0.4, 0.4, 0.4], np.float32)
tri2 = Triangle(p1, p3, p4)
tri2.shadeParam.color = tri1.shadeParam.color
tri2.shadeParam.reflectionStrength = tri1.shadeParam.reflectionStrength

# the scene
objects = [
    sphere1,
    sphere2,
    tri1,
    tri2
]

# how many processes in the process pool
concurrency = 10

pxInds = sum([[(i, j) for j in range(config.imageShape[1])] for i in range(config.imageShape[0])], [])


def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))

splitPxInds = list(split(pxInds, concurrency))

ray_trace_func = partial(ray_trace, config, objects)
pool = Pool(concurrency)
allResults = pool.map(ray_trace_func, splitPxInds, chunksize=1)
allResults = np.asarray(allResults)

result = np.sum(allResults, axis=0)
result = (np.clip(result, 0.0, 1.0) * 255.0).astype(np.uint8)
plt.imshow(result)
plt.show()