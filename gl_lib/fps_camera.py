# a first-person shooter style camera
import glfw
from gl_lib.transmat import *

glfwKeyTranslator={
    glfw.KEY_W: 'w',
    glfw.KEY_A: 'a',
    glfw.KEY_S: 's',
    glfw.KEY_D: 'd'
}


class FPSCamera:

    def __init__(self):
        self.keyboardVelocity = 0.1
        self.mouseVelocity = 0.0012
        self.scrollVelocity = 0.1

        self.eyePos = np.array((0.0, 0.0, 2.0), np.float32)
        self.pitch = 0.0
        self.yaw = -np.pi / 2.0
        self.fov = np.deg2rad(80.0)

    def _get_spherical_coor(self, pitch, yaw):
        return np.asarray(
            (
                np.cos(pitch) * np.cos(yaw),
                np.sin(pitch),
                np.cos(pitch) * np.sin(yaw)
            )
            , np.float32
        )

    def get_eye_pos(self):
        return self.eyePos

    def get_projection_matrix(self, aspect, zNear, zFar):
        return perspective_projection(self.fov, aspect, zNear, zFar)

    def get_view_matrix(self):
        centerDir = self._get_front_dir()
        upDir = self._get_up_dir()

        return look_at(self.eyePos, self.eyePos + centerDir, upDir)

    def _get_front_dir(self):
        return self._get_spherical_coor(self.pitch, self.yaw)

    def _get_up_dir(self):
        return normalized(np.cross(self._get_right_dir(), self._get_front_dir()))

    def _get_right_dir(self):
        return normalized(np.cross(self._get_front_dir(), unit_y()))

    def set_pitch(self, val):
        self.pitch = np.clip(val, -np.deg2rad(89.0), np.deg2rad(89.0))

    def get_pitch(self):
        return self.pitch

    def set_yaw(self, val):
        self.yaw = val

    def get_yaw(self):
        return self.yaw

    def set_fov(self, val):
        self.fov = np.clip(val, np.deg2rad(1.0), np.deg2rad(120.0))

    def get_fov(self):
        return self.fov

    def respond_keypress(self, key):
        if key == 'w':
            self.eyePos += self.keyboardVelocity * self._get_front_dir()
        elif key == 's':
            self.eyePos -= self.keyboardVelocity * self._get_front_dir()
        elif key == 'd':
            self.eyePos += self.keyboardVelocity * self._get_right_dir()
        elif key == 'a':
            self.eyePos -= self.keyboardVelocity * self._get_right_dir()
        else:
            print('invalid keypress: {}'.format(key))

    def respond_mouse_movement(self, xoffset, yoffset):
        self.set_pitch(self.pitch - self.mouseVelocity * yoffset)
        self.set_yaw(self.yaw + self.mouseVelocity * xoffset)

    def respond_scroll(self, yoffset):
        self.set_fov(self.fov + self.scrollVelocity * yoffset)
