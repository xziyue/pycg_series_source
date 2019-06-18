from OpenGL.GL import *
from OpenGL.arrays.vbo import VBO

# because the Python version of glfw changes its naming convention,
# we will always call glfw functinos with the glfw prefix
import glfw
import numpy as np
import platform
import ctypes

windowSize = (800, 600)
windowBackgroundColor = (0.7, 0.7, 0.7, 1.0)

triangleVertices = np.array(
    [-0.5, -0.5, 0.0,  # pos 0
     1.0, 0.0, 0.0,  # color 0
     0.5, -0.5, 0.0,  # pos 1
     1.0, 1.0, 0.0,  # color 1
     0.0, 0.5, 0.0,  # pos 2
     1.0, 0.0, 1.0  # color 2
     ],
    np.float32  # must use 32-bit floating point numbers
)

vertexShaderSource = r'''
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;
out vec3 bColor;
void main()
{
   gl_Position = vec4(aPos, 1.0);
   bColor = aColor;
}
'''

fragmentShaderSource = r'''
#version 330 core
in vec3 bColor;
out vec4 FragColor;
void main()
{
FragColor = vec4(bColor, 1.0f);
}
'''


# compile a shader
# returns the shader id if compilation is successful
# otherwise, raise a runtime error
def compile_shader(shaderType, shaderSource):
    shaderId = glCreateShader(shaderType)
    glShaderSource(shaderId, shaderSource)
    glCompileShader(shaderId)
    success = glGetShaderiv(shaderId, GL_COMPILE_STATUS)
    if not success:
        infoLog = glGetShaderInfoLog(shaderId)
        print('shader compilation error\n')
        print('shader source: \n', shaderSource, '\n')
        print('info log: \n', infoLog)
        raise RuntimeError('unable to compile shader')
    return shaderId


def debug_message_callback(source, msg_type, msg_id, severity, length, raw, user):
    msg = raw[0:length]
    print('debug', source, msg_type, msg_id, severity, msg)


def window_resize_callback(theWindow, width, height):
    global windowSize
    windowSize = (width, height)
    glViewport(0, 0, width, height)


if __name__ == '__main__':

    # initialize glfw
    glfw.init()

    # set glfw config
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    if platform.system().lower() == 'darwin':
        # not sure if this is necessary, but is suggested by learnopengl
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE)

    # create window
    theWindow = glfw.create_window(windowSize[0], windowSize[1], 'Hello Triangle', None, None)
    # make window the current context
    glfw.make_context_current(theWindow)

    if platform.system().lower() != 'darwin':
        # enable debug output
        # doesn't seem to work on macOS
        glEnable(GL_DEBUG_OUTPUT)
        glDebugMessageCallback(GLDEBUGPROC(debug_message_callback), None)

    # set resizing callback function
    glfw.set_framebuffer_size_callback(theWindow, window_resize_callback)

    # create VBO to store vertices
    verticesVBO = VBO(triangleVertices, usage='GL_STATIC_DRAW')
    verticesVBO.create_buffers()

    # create VAO to describe array information
    triangleVAO = glGenVertexArrays(1)

    # bind VAO
    glBindVertexArray(triangleVAO)

    # bind VBO
    verticesVBO.bind()
    # buffer data into OpenGL
    verticesVBO.copy_data()

    # configure the fist 3-vector (pos)
    # arguments: index, size, type, normalized, stride, pointer
    # the stride is 6 * 4 because there are six floats per vertex, and the size of
    # each float is 4 bytes
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * 4, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    # configure the second 3-vector (color)
    # the offset is 3 * 4 = 12 bytes
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * 4, ctypes.c_void_p(3 * 4))
    glEnableVertexAttribArray(1)

    # unbind VBO
    verticesVBO.unbind()
    # unbind VAO
    glBindVertexArray(0)

    # compile shaders
    vertexShaderId = compile_shader(GL_VERTEX_SHADER, vertexShaderSource)
    fragmentShaderId = compile_shader(GL_FRAGMENT_SHADER, fragmentShaderSource)
    # link shaders into a program
    programId = glCreateProgram()
    glAttachShader(programId, vertexShaderId)
    glAttachShader(programId, fragmentShaderId)
    glLinkProgram(programId)
    linkSuccess = glGetProgramiv(programId, GL_LINK_STATUS)
    if not linkSuccess:
        infoLog = glGetProgramInfoLog(programId)
        print('program linkage error\n')
        print('info log: \n', infoLog)
        raise RuntimeError('unable to link program')

    # delete shaders for they are not longer useful
    glDeleteShader(vertexShaderId)
    glDeleteShader(fragmentShaderId)

    # keep rendering until the window should be closed
    while not glfw.window_should_close(theWindow):
        # set background color
        glClearColor(*windowBackgroundColor)
        glClear(GL_COLOR_BUFFER_BIT)

        # use our own rendering program
        glUseProgram(programId)

        # bind VAO
        glBindVertexArray(triangleVAO)
        # draw vertices
        glDrawArrays(GL_TRIANGLES, 0, triangleVertices.size)
        # unbind VAO
        glBindVertexArray(0)

        # tell glfw to poll and process window events
        glfw.poll_events()
        # swap frame buffer
        glfw.swap_buffers(theWindow)

    # clean up VAO
    glDeleteVertexArrays(1, [triangleVAO])
    # clean up VBO
    verticesVBO.delete()

    # terminate glfw
    glfw.terminate()
