import numpy as np

class RoboticArm:

    def __init__(self, armLengths):
        # always assume the origin is (0, 0, 0)
        self.origin = np.zeros(3, np.float)

        self.armLengths = np.array(armLengths, np.float)
        self.numSegments = self.armLengths.size

        # pitch array
        self.ps = np.zeros(self.numSegments, np.float)
        self.ps.fill(np.deg2rad(1.0))
        self.ps[0] = np.deg2rad(89.0)
        # yaw array
        self.ys = np.zeros(self.numSegments, np.float)
        self.ys.fill(np.deg2rad(1.0))
        self.ys[0] = np.deg2rad(1.0)

        # the epsilon used during numerical differentiation
        self.diffEps = 1.0e-3


    def get_arm_position(self):
        return self.get_arm_position_args(self.origin, self.armLengths, self.ps, self.ys)

    def get_all_arm_positions(self):
        return self.get_all_arm_positions_args(self.origin, self.armLengths, self.ps, self.ys)

    @staticmethod
    def get_arm_position_args(origin, armLengths, ps, ys):

        sumPs = np.cumsum(ps)
        sumYs = np.cumsum(ys)

        cosPs = np.cos(sumPs)
        sinPs = np.sin(sumPs)
        sinYs = np.sin(sumYs)
        cosYs = np.cos(sumYs)

        xs = armLengths * cosPs * cosYs
        ys = armLengths * sinPs
        zs = armLengths * cosPs * sinYs

        locations = np.stack([xs, ys, zs], axis=1)
        endPos = np.sum(locations, axis=0) + origin

        return endPos


    @staticmethod
    def get_all_arm_positions_args(origin, armLengths, ps, ys):

        sumPs = np.cumsum(ps)
        sumYs = np.cumsum(ys)

        cosPs = np.cos(sumPs)
        sinPs = np.sin(sumPs)
        sinYs = np.sin(sumYs)
        cosYs = np.cos(sumYs)

        xs = armLengths * cosPs * cosYs
        ys = armLengths * sinPs
        zs = armLengths * cosPs * sinYs

        locations = np.stack([xs, ys, zs], axis=1)
        result = np.cumsum(locations, axis=0) + origin

        return result

    # return new ps, ys if successful
    def solve_new_position(self, newPos):
        newPos = np.asarray(newPos, np.float)

        # check the validity of the newPos
        maxRadius = np.sum(self.armLengths)
        newPosDist = np.linalg.norm(newPos - self.origin)
        if newPosDist > maxRadius:
            raise RuntimeError('new position is not reachable')

        # concatenate ps and ys to form a big parameter vector
        # and compute the partial derivatives
        paramDeltaDiff = []
        paramDeltaSum = []

        for i in range(self.numSegments):
            psm = np.copy(self.ps)
            psp = np.copy(self.ps)
            psm[i] -= self.diffEps
            psp[i] += self.diffEps
            paramDeltaSum.append((psp, self.ys))
            paramDeltaDiff.append((psm, self.ys))

        for i in range(self.numSegments):
            ysm = np.copy(self.ys)
            ysp = np.copy(self.ys)
            ysm[i] -= self.diffEps
            ysp[i] += self.diffEps
            paramDeltaSum.append((self.ps, ysp))
            paramDeltaDiff.append((self.ps, ysm))

        derivatives = []
        for i in range(len(paramDeltaSum)):
            fSum = self.get_arm_position_args(self.origin, self.armLengths, paramDeltaSum[i][0], paramDeltaSum[i][1])
            fDiff = self.get_arm_position_args(self.origin, self.armLengths, paramDeltaDiff[i][0], paramDeltaDiff[i][1])
            deriv = (fSum - fDiff) / (2.0 * self.diffEps)
            derivatives.append(deriv)

        derivatives = np.concatenate(derivatives).reshape((-1, 3)).transpose()

        # compute pseudoinverse for the derivatives
        derivInv = np.linalg.pinv(derivatives, rcond=1.0e-4)

        # compute new set of parameters
        nowPos = self.get_arm_position()
        deltaParam = derivInv @ (newPos - nowPos)

        deltaPs = deltaParam[:self.numSegments]
        deltaYs = deltaParam[self.numSegments:]

        newPs = self.ps + deltaPs
        newYs = self.ys + deltaYs

        # check the precision of this approximation
        actualPos = self.get_arm_position_args(self.origin, self.armLengths, newPs, newYs)
        approxDist = np.linalg.norm(nowPos - newPos)
        error = np.linalg.norm(actualPos - newPos)
        relativeError = error / approxDist

        return newPs, newYs, relativeError


