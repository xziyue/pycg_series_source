from OpenGL.GL import *
import ctypes
import numpy as np

def get_numpy_float32_array_pointer(array):
    assert array.dtype == np.float32
    return array.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

def get_numpy_unit8_array_pointer(array):
    assert array.dtype == np.uint8
    return array.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))

class GLUniform:

    def __init__(self, programId, name, dtype):
        self.programId = programId
        self.name = name

        if dtype == 'float':
            self._valUpdateFunc = self._valUpdateDirect
            self._uniformFunc = glUniform1f
        elif dtype == 'int':
            self._valUpdateFunc = self._valUpdateDirect
            self._uniformFunc = glUniform1i
        elif dtype == 'vec2f':
            self._valUpdateFunc = self._valUpdatePointer
            self._uniformFunc = glUniform2fv
            self._pointerFunc = get_numpy_float32_array_pointer
        elif dtype == 'vec3f':
            self._valUpdateFunc = self._valUpdatePointer
            self._uniformFunc = glUniform3fv
            self._pointerFunc = get_numpy_float32_array_pointer
        elif dtype == 'vec4f':
            self._valUpdateFunc = self._valUpdatePointer
            self._uniformFunc = glUniform4fv
            self._pointerFunc = get_numpy_float32_array_pointer
        elif dtype == 'mat2f':
            self._valUpdateFunc = self._valUpdateMatrixPointer
            self._pointerFunc = get_numpy_float32_array_pointer
            self._uniformFunc = glUniformMatrix2fv
        elif dtype == 'mat3f':
            self._valUpdateFunc = self._valUpdateMatrixPointer
            self._pointerFunc = get_numpy_float32_array_pointer
            self._uniformFunc = glUniformMatrix3fv
        elif dtype == 'mat4f':
            self._valUpdateFunc = self._valUpdateMatrixPointer
            self._pointerFunc = get_numpy_float32_array_pointer
            self._uniformFunc = glUniformMatrix4fv
        else:
            raise RuntimeError('invalid dtype {}'.format(dtype))

    def _valUpdateDirect(self, val):
        location = glGetUniformLocation(self.programId, self.name)
        self._uniformFunc(location, val)

    def _valUpdatePointer(self, val):
        location = glGetUniformLocation(self.programId, self.name)
        matrixPtr = self._pointerFunc(val)
        self._uniformFunc(location, 1, matrixPtr)

    def _valUpdateMatrixPointer(self, val):
        location = glGetUniformLocation(self.programId, self.name)
        matrixPtr = self._pointerFunc(val)
        # transpose set to true to transform from row major to column major
        self._uniformFunc(location, 1, GL_TRUE, matrixPtr)

    def update(self, val):
        self._valUpdateFunc(val)


class GLProgram:

    _glEnumDict = {
        'vertex' : GL_VERTEX_SHADER,
        'fragment' : GL_FRAGMENT_SHADER,
        'geometry' : GL_GEOMETRY_SHADER
    }

    def __init__(self, vertexSource = None, fragmentSource = None, geometrySource = None):
        self.sources = dict()
        self.sources['vertex'] = vertexSource
        self.sources['fragment'] = fragmentSource
        self.sources['geometry'] = geometrySource

        self.programId = None

    def compile_and_link(self):
        assert self.programId is None
        assert self.sources['vertex'] is not None and self.sources['fragment'] is not None

        # compile shaders
        shaderIds = []

        for key, val in self.sources.items():
            if val is None:
                continue

            shaderId = glCreateShader(self._glEnumDict[key])
            shaderIds.append(shaderId)
            glShaderSource(shaderId, val)
            glCompileShader(shaderId)
            success = glGetShaderiv(shaderId, GL_COMPILE_STATUS)
            if not success:
                infoLog = glGetShaderInfoLog(shaderId)
                print('shader compilation error ({} shader)\n'.format(key))
                print('shader source: \n', val, '\n')
                print('info log: \n', infoLog)
                raise RuntimeError('unable to compile shader')

        # link program
        self.programId = glCreateProgram()
        for shaderId in shaderIds:
            glAttachShader(self.programId, shaderId)
        glLinkProgram(self.programId)
        success = glGetProgramiv(self.programId, GL_LINK_STATUS)
        if not success:
            infoLog = glGetProgramInfoLog(self.programId)
            print('program linkage error\n')
            print('info log: \n', infoLog)
            raise RuntimeError('unable to link program')

        # delete shaders
        for shaderId in shaderIds:
            glDeleteShader(shaderId)

    def delete(self):
        glDeleteProgram(self.programId)

    def get_program_id(self):
        assert self.programId is not None
        return self.programId

    def use(self):
        assert self.programId is not None
        glUseProgram(self.programId)



# this class is created mainly for resource management
class GLTexture2D:

    def __init__(self):
        self.textureId = glGenTextures(1)
        assert self.textureId != 0

    def __del__(self):
        self.delete()

    def delete(self):
        if self.textureId != 0:
            glDeleteTextures([self.textureId])
        self.textureId = 0

    def bind(self):
        glBindTexture(GL_TEXTURE_2D, self.textureId)

    def unbind(self):
        glBindTexture(GL_TEXTURE_2D, 0)
