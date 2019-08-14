from Tutorial_5.robotic_arm import *

# equal distance per time quantum
class ActionSeqGenerator:

    def __init__(self, numSteps):
        self.numSteps = numSteps
        self.distEps = 1.0e-3

        # the error that is acceptable in solving for a new position
        self.acceptableRelativeError = 0.03

    # f: the parametric function on [0, 1]
    def generate(self, f, roboticArm):
        # must share the same starting point
        assert np.linalg.norm(f(0.0) - roboticArm.get_arm_position()) < self.distEps

        initPs = roboticArm.ps
        initYs = roboticArm.ys

        xTicks = np.linspace(0.0, 1.0, self.numSteps).tolist()

        result = []
        result.append([0.0, roboticArm.ps, roboticArm.ys])

        lastX = xTicks[0]
        # put the starting point to the end
        xTicks.append(xTicks.pop(0))

        while len(xTicks) > 2:
            farX = xTicks.pop(0)

            attempt = 0
            testX = [farX]

            solved = False

            while attempt < 4:
                newPos = f(testX[-1])
                newPs, newYs, error  = roboticArm.solve_new_position(newPos)
                if error < self.acceptableRelativeError:
                    solved = True
                    break

                # error is too large, shrink the distance
                testX.append((lastX + testX[-1]) / 2.0)
                attempt += 1

            if not solved:
                print('unable to solve for x={} (best relative error: {})'.format(farX, error))

            result.append((testX[-1], newPs, newYs))
            roboticArm.ps = newPs
            roboticArm.ys = newYs

            lastX = testX[-1]

        roboticArm.ps = initPs
        roboticArm.ys = initYs

        return result


