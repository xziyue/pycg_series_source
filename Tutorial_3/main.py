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
from Tutorial_3.shader import *

# import Pillow for loading images
from PIL import Image

windowSize = (800, 600)
windowBackgroundColor = (0.6, 0.6, 0.6, 1.0)
textBackgroundColor = (0.2, 0.6, 0.8)
zNear = 0.1
zFar = 100.0
useBicubic = False

# lighting configurations
lightColor = np.asarray([1.0, 1.0, 1.0], np.float32)
frameColor = np.asarray([0.4, 0.4, 1.0], np.float32)
ambientCoef = 0.1
specularCoef = 0.6
specularP = 64

vertices = np.asarray(
    [
        -0.5, 0.5, 0.0,
        -0.5, -0.5, 0.0,
        0.5, 0.5, 0.0,
        0.5, 0.5, 0.0,
        0.5, -0.5, 0.0,
        -0.5, -0.5, 0.0
    ],
    np.float32
)

textureVertices = np.asarray(
    [
        -0.5, 0.5, 0.0, 0.0, 0.0,
        -0.5, -0.5, 0.0, 0.0, 1.0,
        0.5, 0.5, 0.0, 1.0, 0.0,
        0.5, 0.5, 0.0, 1.0, 0.0,
        0.5, -0.5, 0.0, 1.0, 1.0,
        -0.5, -0.5, 0.0, 0.0, 1.0
    ],
    np.float32
)

camera = FPSCamera()

def debug_message_callback(source, msg_type, msg_id, severity, length, raw, user):
    msg = raw[0:length]
    print('debug', source, msg_type, msg_id, severity, msg)

# stores which keys are pressed and handle key press in the main loop
keyArray = np.array([False] * 300, np.bool)

def window_keypress_callback(theWindow, key, scanCode, action, mods):
    global useBicubic

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
            useBicubic = not useBicubic
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

# resource-taking objects
resObjs= []

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
    theWindow = glfw.create_window(windowSize[0], windowSize[1], 'Texture & Text', None, None)
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

    vertexVBO = VBO(vertices, usage='GL_STATIC_DRAW')
    vertexVBO.create_buffers()
    textureVBO = VBO(textureVertices, usage = 'GL_STATIC_DRAW')
    textureVBO.create_buffers()

    frameVAO = glGenVertexArrays(1)
    glBindVertexArray(frameVAO)
    vertexVBO.bind()
    vertexVBO.copy_data()
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glBindVertexArray(0)

    textureVAO = glGenVertexArrays(1)
    glBindVertexArray(textureVAO)
    textureVBO.bind()
    textureVBO.copy_data()
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * ctypes.sizeof(ctypes.c_float),
                          ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))
    glEnableVertexAttribArray(1)
    glBindVertexArray(0)

    # create programs and uniforms
    frameRenderProgram = GLProgram(frameVertexShaderSource, frameFragmentShaderSource)
    frameRenderProgram.compile_and_link()
    frameUniformInfos = [
        ('model', 'mat4f'),
        ('view', 'mat4f'),
        ('projection', 'mat4f'),
        ('objectColor', 'vec3f'),
        ('lightColor', 'vec3f'),
        ('viewPos', 'vec3f'),
        ('lightPos', 'vec3f'),
        ('ambientCoef', 'float'),
        ('specularCoef', 'float'),
        ('specularP', 'int')
    ]
    frameRenderUniforms = create_uniform(frameRenderProgram.get_program_id(), frameUniformInfos)

    textureRenderProgram = GLProgram(textureVertexShaderSource, textureFragmentShaderSource)
    textureRenderProgram.compile_and_link()
    textureUniformInfos = [
        ('model', 'mat4f'),
        ('view', 'mat4f'),
        ('projection', 'mat4f'),
        ('textureSize', 'vec2f')
    ]
    textureRenderUniforms = create_uniform(textureRenderProgram.get_program_id(), textureUniformInfos)

    textureBicubicRenderProgram = GLProgram(textureVertexShaderSource, textureBicubicFragmentShaderSource)
    textureBicubicRenderProgram.compile_and_link()
    textureBicubicRenderUniforms = create_uniform(textureBicubicRenderProgram.get_program_id(), textureUniformInfos)

    # create texture
    image = np.asarray(Image.open('orphea.png'), np.uint8)
    imageAspect = image.shape[0] / image.shape[1]
    imageSize = np.asarray([image.shape[1], image.shape[0]], np.float32)

    # unpack alignment first
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    texture = GLTexture2D()
    texture.bind()

    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGB,
        image.shape[1],
        image.shape[0],
        0,
        GL_RGB,
        GL_UNSIGNED_BYTE,
        get_numpy_unit8_array_pointer(image)
    )

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    # in this case, GL_NEAREST and GL_LINEAR should make little difference
    # because only the center of pixels are used in the shader
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    texture.unbind()
    resObjs.append(texture)

    textDrawer = TextDrawer_Outlined()
    textDrawer.load_font('../misc/STIX2Text-Regular.otf', 30 * 64, 1 * 64)
    resObjs.append(textDrawer)

    # change drawing mode
    # glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

    # keep rendering until the window should be closed
    while not glfw.window_should_close(theWindow):
        # set background color
        glClearColor(*windowBackgroundColor)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # render the frame
        frameRenderProgram.use()
        aspect = windowSize[0] / windowSize[1]
        frameRenderUniforms['projection'].update(camera.get_projection_matrix(aspect, zNear, zFar))
        frameRenderUniforms['view'].update(camera.get_view_matrix())
        frameRenderUniforms['model'].update(scale(1.0 / imageAspect, 1.0, 1.0))
        frameRenderUniforms['objectColor'].update(frameColor)
        frameRenderUniforms['lightColor'].update(lightColor)
        frameRenderUniforms['viewPos'].update(camera.get_eye_pos())
        frameRenderUniforms['lightPos'].update(camera.get_eye_pos())
        frameRenderUniforms['ambientCoef'].update(ambientCoef)
        frameRenderUniforms['specularCoef'].update(specularCoef)
        frameRenderUniforms['specularP'].update(specularP)

        glBindVertexArray(frameVAO)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)

        if useBicubic:
            textureProgram = textureBicubicRenderProgram
            textureUniforms = textureBicubicRenderUniforms
        else:
            textureProgram = textureRenderProgram
            textureUniforms = textureRenderUniforms

        # render the texture
        textureProgram.use()
        glActiveTexture(GL_TEXTURE0)
        texture.bind()
        textureUniforms['projection'].update(camera.get_projection_matrix(aspect, zNear, zFar))
        textureUniforms['view'].update(camera.get_view_matrix())

        # modify its model matrix so that it is above the frame a little bit and smaller than the frame
        textureUniforms['model'].update(
            scale(0.95, 0.95, 1.0) @ translate(0.0, 0.0, 0.01) @ scale(1.0 / imageAspect, 1.0, 1.0)
        )
        textureUniforms['textureSize'].update(imageSize)

        glBindVertexArray(textureVAO)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)


        textDrawer.draw_text('sample text\nheroes\nOrphea', (5, windowSize[1] - 5), windowSize, scale=(1.0, 1.0),
                             backColor=textBackgroundColor)

        # respond key press
        keyboard_respond_func()
        # tell glfw to poll and process window events
        glfw.poll_events()
        # swap frame buffer
        glfw.swap_buffers(theWindow)

    for obj in resObjs:
        obj.delete()

    # terminate glfw
    glfw.terminate()
