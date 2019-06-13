from OpenGL.GL import *
import ctypes
import numpy as np

class Uniform:

    def __init__(self, type, programId):
        self.programId = programId

        if type == 'float':
            self._valUpdateFunc = self._valUpdateDirect
            self.uniformFunc = glUniform1f
        elif type == 'int':
            self._valUpdateFunc = self._valUpdateDirect
            self.uniformFunc = glUniform1d
        elif type == 'mat2':
            self._valUpdateFunc = self._valUpdatePointer
            self._pointerFunc = self._getNumpyFloat32ArrayPointer
            self._uniformFunc = glUniform2fv
        elif type == 'mat3':
            pass
        elif type == 'mat4':
            pass

    def _valUpdateDirect(self, val):
        pass

    def _valUpdatePointer(self, val):
        pass

    def _getNumpyFloat32ArrayPointer(self, array):
         return array.ctypes.data_as(ctypes.POINTER(ctypes.c_float))