import numpy as np

_nonZeroEps = 1.0e-3

def _check_non_zero(array):
    norm = np.linalg.norm(array)
    assert abs(norm) > _nonZeroEps
    return norm

def normalized(array):
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

def _cross_product_matrix(axis):
    return np.asarray(
        (
            (0, -axis[2], axis[1]),
            (axis[2], 0, -axis[0]),
            (-axis[1], axis[0], 0)
         ),
        np.float32
    )

def rotate(axis, angle, degree=False):
    assert axis.size == 3

    axis = normalized(axis)

    if degree:
        angle = np.deg2rad(angle)

    mat3 = np.cos(angle) * np.identity(3, dtype=np.float32) + np.sin(angle) * _cross_product_matrix(axis) + \
           (1 - np.cos(angle)) * np.outer(axis, axis)

    result = np.zeros((4, 4), np.float32)
    result[:3, :3] = mat3
    result[3, 3] = 1.0

    return result

def look_at(eye, center, up):
    z = normalized(eye - center)
    x = normalized(np.cross(up, z))
    y = np.cross(z, x)

    result = np.zeros((4, 4), np.float32)
    result[0, :3] = x
    result[1, :3] = y
    result[2, :3] = z
    result[0, 3] = -x.dot(eye)
    result[1, 3] = -y.dot(eye)
    result[2, 3] = -z.dot(eye)
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
    result[3, 2] = -1.0
    result[2, 3] = -(2.0 * zFar * zNear) / (zFar - zNear)

    return result


def orthographic_projection(left, right, bottom, top, zNear, zFar):
    assert abs(right - left) > _nonZeroEps
    assert abs(top - bottom) > _nonZeroEps
    assert abs(zNear - zFar) > _nonZeroEps

    result = np.zeros((4, 4), np.float32)
    result[0, 0] = 2.0 / (right - left)
    result[1, 1] = 2.0 / (top - bottom)
    result[2, 2] = -2.0 / (zFar - zNear)
    result[3, 3] = 1.0
    result[0, 3] = -(right + left) / (right - left)
    result[1, 3] = -(top + bottom) / (top - bottom)
    result[2, 3] = -(zFar + zNear) / (zFar - zNear)

    return result