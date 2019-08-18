from OpenGL.GL import *
from OpenGL.arrays.vbo import VBO
import glfw
import numpy as np
import platform as pyPlatform
import ctypes
from datetime import datetime

# add last folder into PYTHONPATH
import sys, os

lastFolder = os.path.split(os.getcwd())[0]
sys.path.append(lastFolder)

from gl_lib.transmat import *
from gl_lib.utility import *
from gl_lib.fps_camera import *
from gl_lib.gl_screenshot import save_screenshot_rgb
import gl_lib.text_drawer
from gl_lib.text_drawer import TextDrawer, TextDrawer_Outlined
from misc.sphere_tessellation import uniform_tessellate_half_sphere
from misc.cylinder_tessellation import uniform_tessellate_half_cylinder
from Tutorial_5.shader import *

windowSize = (800, 600)
windowBackgroundColor = (0.3, 0.3, 0.3, 1.0)
zNear = 0.1
zFar = 300.0
deltaTime = 0.01 # dt used in simulation
targetFPS = 60
frameInterval = 1 / targetFPS

# lighting configurations
lightColor = np.asarray([1.0, 1.0, 1.0], np.float32)
clothColor = np.asarray([0.3, 0.5, 0.8], np.float32)
ambientCoef = 0.1
specularCoef = 0.6
specularP = 256

# the camera
camera = FPSCamera()
camera.eyePos = np.array((0.0, 0.0, 5.0), np.float32)

from Tutorial_6.spring_mass_grid import SpringMassGrid
grid = SpringMassGrid(14, 14, [0, 0, 0], 4.0, 8.0, 0.2, 0.01, 0.05, 0.02)
# initialize grid array
gridArray = np.concatenate([grid.pos.squeeze(), grid.compute_normal()], axis=2)
gridArray = gridArray.flatten().astype(np.float32)

def convert_grid_index(_2dInd):
    return _2dInd[0] * grid.numCols + _2dInd[1]

# iniitilze element array
elementArray = []
for i in range(grid.numRows - 1):
    for j in range(grid.numCols - 1):
        tri1Indices = [
            (i, j),
            (i + 1, j),
            (i + 1, j + 1)
        ]
        tri1Indices = list(map(convert_grid_index, tri1Indices))

        tri2Indices = [
            (i, j),
            (i + 1, j + 1),
            (i, j + 1)
        ]
        tri2Indices =  list(map(convert_grid_index, tri2Indices))
        elementArray.extend(tri1Indices)
        elementArray.extend(tri2Indices)


elementArray = np.asarray(elementArray, np.uint32)

def debug_message_callback(source, msg_type, msg_id, severity, length, raw, user):
    msg = raw[0:length]
    print('debug', source, msg_type, msg_id, severity, msg)


# stores which keys are pressed and handle key press in the main loop
keyArray = np.array([False] * 300, np.bool)

drawingModes = [GL_FILL, GL_LINE]
nowModeIndex = 0

def window_keypress_callback(theWindow, key, scanCode, action, mods):
    global useBicubic, controlId, drawingModes, nowModeIndex

    if key == glfw.KEY_UNKNOWN:
        return

    if action == glfw.PRESS:
        if key == glfw.KEY_ESCAPE:
            # respond escape here
            glfw.set_window_should_close(theWindow, True)
        elif key == glfw.KEY_P:
            # respond screenshot keypress
            nowTime = datetime.now()
            timeString = nowTime.strftime('%Y-%m-%d_%H:%M:%S')
            screenshotFmt = 'screenshot_{}.png'
            save_screenshot_rgb(screenshotFmt.format(timeString), windowSize)
        elif key == glfw.KEY_O:
            nowModeIndex = (nowModeIndex + 1) % len(drawingModes)
            glPolygonMode(GL_FRONT_AND_BACK, drawingModes[nowModeIndex])
        else:
            keyArray[key] = True
    elif action == glfw.RELEASE:
        keyArray[key] = False


def keyboard_respond_func():
    global keyArray

    keyPressed = np.where(keyArray == True)
    for key in keyPressed[0]:
        if key in glfwKeyTranslator:
            camera.respond_keypress(glfwKeyTranslator[key])


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


def create_uniform(programId, infos):
    result = dict()
    for name, tp in infos:
        uniform = GLUniform(programId, name, tp)
        result[name] = uniform
    return result


if __name__ == '__main__':

    # initialize glfw
    glfw.init()

    # set glfw config
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    if pyPlatform.system().lower() == 'darwin':
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE)

    # create window
    theWindow = glfw.create_window(windowSize[0], windowSize[1], 'Cloth Simulation', None, None)
    # make window the current context
    glfw.make_context_current(theWindow)

    # enable z-buffer
    glEnable(GL_DEPTH_TEST)

    if pyPlatform.system().lower() != 'darwin':
        # enable debug output
        # doesn't seem to work on macOS
        glEnable(GL_DEBUG_OUTPUT)
        glDebugMessageCallback(GLDEBUGPROC(debug_message_callback), None)
    # set resizing callback function
    # glfw.set_framebuffer_size_callback(theWindow, window_resize_callback)

    glfw.set_key_callback(theWindow, window_keypress_callback)
    # disable cursor
    glfw.set_input_mode(theWindow, glfw.CURSOR, glfw.CURSOR_DISABLED)

    glfw.set_cursor_pos_callback(theWindow, window_cursor_callback)
    # initialize cursor position
    cursorPos = glfw.get_cursor_pos(theWindow)

    glfw.set_scroll_callback(theWindow, window_scroll_callback)


    gridVBO = VBO(gridArray, usage='GL_DYNAMIC_DRAW')
    gridVBO.create_buffers()
    gridEBO = VBO(elementArray, usage='GL_STATIC_DRAW', target='GL_ELEMENT_ARRAY_BUFFER')
    gridEBO.create_buffers()

    gridVAO = glGenVertexArrays(1)

    glBindVertexArray(gridVAO)
    gridVBO.bind()
    gridVBO.copy_data()
    gridEBO.bind()
    gridEBO.copy_data()
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * ctypes.sizeof(ctypes.c_float),
                          ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))
    glEnableVertexAttribArray(1)
    glBindVertexArray(0)
    gridVBO.unbind()

    renderProgram = GLProgram(vertexShaderSource, fragmentShaderSource)
    renderProgram.compile_and_link()

    lineProgram = GLProgram(lineVertexShaderSource, lineFragmentShaderSource, lineGeometryShaderSource)
    lineProgram.compile_and_link()

    # create uniforms
    uniformInfos = [
        ('projection', 'mat4f'),
        ('view', 'mat4f'),
        ('model', 'mat4f'),
        ('lightPos', 'vec3f'),
        ('viewPos', 'vec3f'),
        ('lightColor', 'vec3f'),
        ('objectColor', 'vec3f'),
        ('ambientCoef', 'float'),
        ('specularCoef', 'float'),
        ('specularP', 'int')
    ]


    uniforms = create_uniform(renderProgram.get_program_id(), uniformInfos)

    lastFrameTime = glfw.get_time()

    # keep rendering until the window should be closed
    while not glfw.window_should_close(theWindow):

        # set background color
        glClearColor(*windowBackgroundColor)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        aspect = windowSize[0] / windowSize[1]

        renderProgram.use()

        # update shading related uniforms
        uniforms['viewPos'].update(camera.get_eye_pos())
        uniforms['lightPos'].update(camera.get_eye_pos())
        uniforms['lightColor'].update(lightColor)
        uniforms['ambientCoef'].update(ambientCoef)
        uniforms['specularCoef'].update(specularCoef)
        uniforms['specularP'].update(specularP)
        uniforms['projection'].update(camera.get_projection_matrix(aspect, zNear, zFar))
        uniforms['view'].update(camera.get_view_matrix())
        uniforms['objectColor'].update(clothColor)


        rightShift = grid.numCols * grid.initLength / 2.0
        downShift = grid.numRows * grid.initLength / 2.0
        uniforms['model'].update(translate(-rightShift, downShift, 0.0))

        # compute new parameters
        grid.get_new_state_and_update(deltaTime)
        # compute normal
        gridArray = np.concatenate([grid.pos.squeeze(), grid.normal], axis=2)
        gridArray = gridArray.flatten().astype(np.float32)
        # update buffer
        gridVBO.set_array(gridArray)
        gridVBO.bind()
        gridVBO.copy_data()
        gridVBO.unbind()

        glBindVertexArray(gridVAO)
        glDrawElements(GL_TRIANGLES, elementArray.size, GL_UNSIGNED_INT, ctypes.c_void_p(0))
        glBindVertexArray(0)

        # respond key press
        keyboard_respond_func()
        # tell glfw to poll and process window events
        glfw.poll_events()
        # swap frame buffer
        glfw.swap_buffers(theWindow)



    # clean up VAO
    allVAO = [gridVAO]
    glDeleteVertexArrays(len(allVAO), allVAO)
    # clean up VBO
    gridVBO.delete()
    gridEBO.delete()
    # clean up program
    renderProgram.delete()

    # terminate glfw
    glfw.terminate()
