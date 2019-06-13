import numpy as np

_nonZeroEps = 1.0e-3

def _check_non_zero(array):
    norm = np.linalg.norm(array)
    assert abs(norm) > _nonZeroEps
    return norm

def _normalized(array):
    norm = _check_non_zero(array)
    return array / norm

def unit_x():
    return np.array((1, 0, 0), np.float32)

def unit_y():
    return np.array((0, 1, 0), np.float32)

def unit_z():
    return np.array((0, 0, 1), np.float32)

def scale(*args):
    assert len(args) == 3
    
    result = np.zeros((4, 4), np.float32)
    result[0, 0] = args[0]
    result[1, 1] = args[1]
    result[2, 2] = args[2]
    result[3, 3] = 1.0

    return result

def translate(*args):
    assert len(args) == 3
    result = np.identity(4, dtype=np.float32)
    result[0, 3] = args[0]
    result[1, 3] = args[1]
    result[2, 3] = args[2]

    return result

def rotate(axis, angle, degree=False):
    assert axis.size == 3

    if degree:
        angle = np.deg2rad(angle)

    return np.cos(angle) * np.identity(4, dtype=np.float32) + np.sin(angle) * np.cross(axis, axis) + \
           (1 - np.cos(angle)) * np.outer(angle, angle)

def look_at(eye, center, up):
    z = _normalized(eye - center)
    x = np.cross(up, z)
    y = np.cross(z, x)
    x = _normalized(x)
    y = _normalized(y)

    result = np.zeros((4, 4), np.float32)
    result[:3, 0] = x
    result[:3, 1] = y
    result[:3, 2] = z
    result[3, 0] = -x.dot(eye)
    result[3, 1] = -y.dot(eye)
    result[3, 2] = -z.dot(eye)
    result[3, 3] = 1.0

    return result

def perspective_projection(fovy, aspect, zNear, zFar, degree=False):
    assert abs(aspect) > _nonZeroEps
    assert abs(zNear - zFar) > _nonZeroEps
    if degree:
        fovy = np.deg2rad(fovy)

    tanHalf = np.tan(fovy / 2.0)

    result = np.zeros((4, 4), np.float32)
    result[0, 0] = 1.0 / (aspect * tanHalf)
    result[1, 1] = 1.0 / tanHalf
    result[2, 2] = -(zFar + zNear)/(zFar - zNear)
    result[2, 3] = -1.0
    result[3, 2] = -(2.0 * zFar * zNear) / (zFar - zNear)

    return result
