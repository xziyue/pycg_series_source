from OpenGL.GL import *
from OpenGL.arrays.vbo import VBO
import glfw
import numpy as np
import platform
import ctypes

from gl_lib.transmat import *
from gl_lib.utility import GLUniform, GLProgram
from gl_lib.fps_camera import *

# program configurations
windowSize = (800, 600)
windowBackgroundColor = (0.7, 0.7, 0.7, 1.0)
zNear = 0.1
zFar = 300.0

objectColor = np.asarray([0.5, 0.3, 0.4], np.float32)

# the camera
camera = FPSCamera()

# vertices and elements
vertices = np.asarray(
    [
        -0.5, 0.5, -0.5,
        -0.5, -0.5, -0.5,
        0.5, -0.5, -0.5,
        0.5, 0.5, -0.5,
        -0.5, 0.5, -1.5,
        -0.5, -0.5, -1.5,
        0.5, -0.5, -1.5,
        0.5, 0.5, -1.5,
    ],
    np.float32
)

elements = np.asarray(
    [
        0, 2, 1,
        0, 3, 2,
        1, 5, 4,
        1, 2, 5,
        2, 6, 5,
        2, 3, 6,
        3, 6, 7,
        3, 7, 0,
        0, 1, 4,
        0, 4, 7,
        7, 5, 4,
        7, 6, 5
    ]
    , np.uint32
)

# compute normal for each surface
normals = []
tempVertices = vertices.reshape((-1, 3))
for i in range(0, elements.size, 3):
    triVertices = tempVertices[elements[i : i + 3]]
    normals.append(normalized(np.cross(triVertices[1] - triVertices[0], triVertices[2] - triVertices[0])))

normals = np.asarray(normals, np.float32).flatten()

vertexShaderSource = r'''
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

out vec3 bNormal;

void main()
{
   bNormal = mat3(transpose(inverse(model))) * aNormal;
   gl_Position = projection * view * model * vec4(aPos, 1.0);
}
'''

fragmentShaderSource = r'''
#version 330 core
in vec3 bNormal;
out vec4 FragColor;

uniform vec3 objectColor;
uniform vec3 color;
uniform vec3 viewPos;
uniform vec3 lightPos;
uniform float ambientCoef;
uniform float specularCoef;
uniform int specularP;

void main()
{
FragColor = vec4(color, 1.0f);
}
'''

cursorPos = None

def debug_message_callback(source, msg_type, msg_id, severity, length, raw, user):
    msg = raw[0:length]
    print('debug', source, msg_type, msg_id, severity, msg)


def window_keypress_callback(theWindow, key, scanCode, action, mods):
    if key in glfwKeyTranslator and (action == glfw.PRESS or action == glfw.REPEAT):
        camera.respond_keypress(glfwKeyTranslator[key])
    elif key == glfw.KEY_ESCAPE and action == glfw.PRESS:
        glfw.set_window_should_close(theWindow, True)

def window_resize_callback(theWindow, width, height):
    global windowSize
    windowSize = (width, height)
    glViewport(0, 0, width, height)

def window_cursor_callback(theWindow, xPos, yPos):
    global cursorPos
    xOffset = xPos - cursorPos[0]
    yOffset = yPos - cursorPos[1]
    camera.respond_mouse_movement(xOffset, yOffset)
    cursorPos = (xPos, yPos)

def window_scroll_callback(theWindow, xOffset, yOffset):
    camera.respond_scroll(yOffset)

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
    theWindow = glfw.create_window(windowSize[0], windowSize[1], '3D Lighting', None, None)
    # make window the current context
    glfw.make_context_current(theWindow)

    # enable z-buffer
    glEnable(GL_DEPTH_TEST)

    if platform.system().lower() != 'darwin':
        # enable debug output
        # doesn't seem to work on macOS
        glEnable(GL_DEBUG_OUTPUT)
        glDebugMessageCallback(GLDEBUGPROC(debug_message_callback), None)
    # set resizing callback function
    #glfw.set_framebuffer_size_callback(theWindow, window_resize_callback)

    glfw.set_key_callback(theWindow, window_keypress_callback)
    # disable cursor
    glfw.set_input_mode(theWindow, glfw.CURSOR, glfw.CURSOR_DISABLED)

    glfw.set_cursor_pos_callback(theWindow, window_cursor_callback)
    # initialize cursor position
    cursorPos = glfw.get_cursor_pos(theWindow)

    glfw.set_scroll_callback(theWindow, window_scroll_callback)

    # create VBOs to store vertices, normals and elements
    verticesVBO = VBO(vertices, usage='GL_STATIC_DRAW')
    verticesVBO.create_buffers()
    elementsVBO = VBO(elements, usage = 'GL_STATIC_DRAW', target='GL_ELEMENT_ARRAY_BUFFER')
    elementsVBO.create_buffers()
    normalsVBO = VBO(normals, usage = 'GL_STATIC_DRAW')
    normalsVBO.create_buffers()


    # create VAO to describe array information
    triangleVAO = glGenVertexArrays(1)

    # bind VAO
    glBindVertexArray(triangleVAO)

    # bind vertex VBO
    verticesVBO.bind()
    # buffer data into OpenGL
    verticesVBO.copy_data()

    # bind element VBO
    elementsVBO.bind()
    elementsVBO.copy_data()

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    # bind normal VBO
    normalsVBO.bind()
    normalsVBO.copy_data()

    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 3 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    # unbind normal VBO
    normalsVBO.unbind()
    # no need to unbind element VBO
    # unbind VAO
    glBindVertexArray(0)

    renderProgram = GLProgram(vertexShaderSource, fragmentShaderSource)
    renderProgram.compile_and_link()

    # create uniform
    projectionUniform = GLUniform(renderProgram.get_program_id(), 'projection', 'mat4f')
    viewUniform = GLUniform(renderProgram.get_program_id(), 'view', 'mat4f')
    modelUniform = GLUniform(renderProgram.get_program_id(), 'model', 'mat4f')
    colorUniform = GLUniform(renderProgram.get_program_id(), 'color', 'vec3f')

    # change drawing mode
    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

    # keep rendering until the window should be closed
    while not glfw.window_should_close(theWindow):
        # set background color
        glClearColor(*windowBackgroundColor)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # use our own rendering program
        renderProgram.use()
        # update uniform
        aspect = windowSize[0] / windowSize[1]
        projectionUniform.update(camera.get_projection_matrix(aspect, zNear, zFar))
        viewUniform.update(camera.get_view_matrix())
        modelUniform.update(scale(1.0, 1.0, 1.0))
        colorUniform.update(objectColor)

        # bind VAO
        glBindVertexArray(triangleVAO)
        # draw vertices
        glDrawElements(GL_TRIANGLES, elements.size, GL_UNSIGNED_INT, ctypes.c_void_p(0))
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
    elementsVBO.delete()
    normalsVBO.delete()
    # clean up program
    renderProgram.delete()

    # terminate glfw
    glfw.terminate()
