import numpy as np


class SpringMassGrid:

    def __init__(self, numRows, numCols, topLeftPos, gravity, stiffness, initLength, pointMass, dampingCoef, airCoef):
        assert numRows > 2
        assert numCols > 2
        # we need to ignore division errors as we need to constantly divide vectors by zero
        np.seterr(divide='ignore', invalid='ignore')

        self.numRows = numRows
        self.numCols = numCols
        self.topLeftPos = np.asarray(topLeftPos, np.float)
        self.gravity = gravity
        self.stiffness = stiffness
        self.initLength = initLength
        self.pointMass = pointMass
        self.dampingCoef = dampingCoef
        self.windCoef = airCoef

        self.acc = np.zeros((numRows, numCols, 3), np.float)
        self.pos = np.zeros((numRows, numCols, 1, 3), np.float) # pos needs a different shape for broadcasting
        self.vlc = np.zeros((numRows, numCols, 3), np.float)

        # initialize position
        for i in range(numRows):
            for j in range(numCols):
                self.pos[i][j][0] = topLeftPos + np.asarray([0.0, -initLength * i, 0.0], np.float) +\
                                        np.asarray([initLength * j, 0.0, 0.0])

        # the springs

        self.springSetting = [
            (1, 0), # structural
            (0, 1), # structural
            (-1, 0), # structural
            (0, -1), # structural
            (-1, -1), # shear
            (-1, 1), # shear
            (1, -1), #shear
            (1, 1), #shear
            (0, 2), #bend
            (0, -2), # bend
            (2, 0), # bend
            (-2, 0)
        ]

        # the element indices for springs
        self.springIndices = np.empty((numRows, numCols), dtype=np.object)
        for i in range(numCols):
            for j in range(numRows):
                allIndices = [(x[0] + i, x[1] + j) for x in self.springSetting]
                self.springIndices[i][j] = self._check_and_fill_indices(allIndices, (i, j), 6)

        self.springIndices = self._get_flat_indices(self.springIndices)

        # the initial lengths of each spring
        self.springInitLengths = np.linalg.norm(np.asarray(self.springSetting, np.float) * self.initLength, axis = 1)

        self.normal = self.compute_normal()

    def _is_index_valid(self, index):
        if index[0] >= 0 and index[0] < self.numRows and index[1] >= 0 and index[1] < self.numCols:
            return True
        return False

    def _check_and_fill_indices(self, lst, nowIndex, targetLength):
        validIndices = []
        for i in range(len(lst)):
            if self._is_index_valid(lst[i]):
                validIndices.append(lst[i])
            else:
                validIndices.append(nowIndex)
        validIndices = np.asarray(validIndices)
        result = [validIndices[:, 0], validIndices[:, 1], np.zeros(validIndices.shape[0], np.int)]
        return result

    def _get_flat_indices(self, indices):
        indices = np.asarray(indices)
        indicesFlat = indices.flatten()
        allX = []
        allY = []
        for i in range(indicesFlat.shape[0]):
            allX.append(indicesFlat[i][0])
            allY.append(indicesFlat[i][1])
        allX = np.concatenate(allX)
        allY = np.concatenate(allY)
        return (allX, allY)

    def _extract_points_by_indices(self, points, indices):
        result = self.pos[indices]
        result = result.reshape((points.shape[0], points.shape[1], -1, 3))
        return result

    def _compute_tri_normal(self, p1, p2, p3):
        vec1 = p2 - p1
        vec2 = p3 - p1
        normal = np.cross(vec1, vec2)
        norm = np.linalg.norm(normal)
        if norm < 1.0e-3:
            return np.zeros(3, np.float)
        else:
            return normal / norm

    def compute_normal(self):
        normalArray = [[[] for _ in range(self.numCols)] for _ in range(self.numRows)]

        def compute_and_update(lstOfIndices):
            normal = self._compute_tri_normal(
                *[self.pos[p] for p in lstOfIndices]
            )
            for p in lstOfIndices:
                normalArray[p[0]][p[1]].append(normal)

        for i in range(self.numRows - 1):
            for j in range(self.numCols - 1):

                tri1Indices = [
                    (i, j),
                    (i + 1, j),
                    (i + 1, j + 1)
                ]

                compute_and_update(tri1Indices)

                tri2Indices = [
                    (i, j),
                    (i + 1, j + 1),
                    (i, j + 1)
                ]

                compute_and_update(tri2Indices)

        result = np.zeros((self.numRows, self.numCols, 3), np.float)

        # average the surface normals
        for i in range(self.numRows):
            for j in range(self.numCols):
                mean = np.mean(normalArray[i][j], axis=0)
                norm = np.linalg.norm(mean)
                if norm < 1.0e-3:
                    mean = np.zeros(3, np.float)
                else:
                    mean /= norm
                result[i, j, :] = mean


        return result

    # compute the force each point receives at this given time
    def compute_force(self):

        force = np.zeros((self.numRows, self.numCols, 3), np.float)

        # gravity (assume that gravity is along negative y axis)
        force[:, :] += np.asarray([0.0, -self.gravity * self.pointMass, 0.0], np.float)

        # viscous damping
        force[:, :] += -self.dampingCoef * self.vlc

        # compute the internal force of the spring grid
        springLink = self._extract_points_by_indices(self.pos, self.springIndices)
        springVec = springLink - self.pos
        springLength = np.linalg.norm(springVec, axis=3) #
        springNormalVec = np.nan_to_num(springVec / springLength[:, :, :, None], 0.0)
        springDelta = (springVec - self.springInitLengths[:, None] * springNormalVec) * self.stiffness
        springTotal = np.sum(springDelta, axis=2)
        force += springTotal

        # simulate wind at a constant part of the space
        halfCol = self.numCols // 2
        halfX = halfCol * self.initLength
        posX = self.pos[:, :, 0, 0]
        halfRow = self.numRows // 2
        halfY = -halfRow * self.initLength
        posY = self.pos[:, :, 0, 1]
        notAffectedPos = np.where(np.bitwise_or(posX < halfX, posY > halfY))

        windSpeed = np.asarray([0, 0, -1], np.float)
        windDiff = windSpeed - self.normal
        windDot = np.zeros((self.numRows, self.numCols, 1), np.float)
        for i in range(self.numRows):
            for j in range(self.numCols):
                windDot[i, j, 0] = windDiff[i, j, :] @ self.normal[i, j, :]
        windForce = self.windCoef * windDot *  self.normal

        # cancel wind force for those parts that are not affected
        windForce[(notAffectedPos[0], notAffectedPos[1], ...)] = [0, 0, 0]
        force[:, :] += windForce

        # assume that the top two corners are hung
        force[0, 0, :] = [0, 0, 0]
        force[0, self.numCols - 1, :] = [0, 0, 0]

        return force

    def get_new_state(self, dt):
        newAcc = self.compute_force() / self.pointMass
        newVlc = self.vlc + dt * newAcc
        newPos = self.pos + dt * newVlc[:, :, None, :]

        return newAcc, newVlc, newPos

    def get_new_state_and_update(self, dt):
        newAcc, newVlc, newPos = self.get_new_state(dt)
        self.acc = newAcc
        self.vlc = newVlc
        self.pos = newPos
        self.normal = self.compute_normal()
        return np.copy(newAcc), np.copy(newVlc), np.copy(newPos)