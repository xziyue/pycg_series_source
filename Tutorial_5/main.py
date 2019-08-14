from scipy.interpolate import interp1d
from gl_lib.transmat import *
from Tutorial_5.robotic_arm import *
from Tutorial_5.generate_action_sequence import *


tTicks = np.linspace(0, 2 * np.pi, 300)
roboticArm = RoboticArm([1.0, 1.2, 1.5, 0.8])
actionGen = ActionSeqGenerator(300)

def get_ellipse(t):
    x = np.sin(t)
    y = 2.0 * np.cos(t)
    z = np.zeros(t.size, np.float)
    w = np.ones(t.size, np.float)
    return np.stack([x, y, z, w], axis=1)

ellipsePoints = get_ellipse(tTicks).transpose()
initPos = roboticArm.get_arm_position()
transformedPoints = translate(initPos[0], initPos[1], initPos[2]) @ rotate(unit_x(), -20.0, True) @ scale(1.8, 1.5, 1.4) @translate(0.0, -2.0, 0.0) @ ellipsePoints
transformedPoints = transformedPoints[:3, :]
ellipseFunc = interp1d(tTicks / tTicks.max(), transformedPoints)

print('solving inverse kinematics...')
actionResult = actionGen.generate(ellipseFunc, roboticArm)
print('finished!')

ts, ps, ys = zip(*actionResult)
ts = np.asarray(ts)
ps = np.asarray(ps)
ys = np.asarray(ys)
pFunc = interp1d(ts / ts.max(), ps.transpose())
yFunc = interp1d(ts / ts.max(), ys.transpose())

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
windowBackgroundColor = (0.2, 0.2, 0.2, 1.0)
zNear = 0.1
zFar = 300.0
numFramePerLoop = 300

jointScale = 0.2
armScale = 0.12
armOffset = 0.08
pathLineWidth = 0.03

# for drawing the actual path on the screen
actualPathTicks = np.linspace(0.0, 1.0, 100)

# lighting configurations
lightColor = np.asarray([1.0, 1.0, 1.0], np.float32)
jointColor = np.asarray([0.2, 0.8, 0.3], np.float32)
cylinderColor = np.asarray([0.7, 0.7, 0.7], np.float32)
pathColor = np.asarray([1.0, 1.0, 0.0], np.float32)
ambientCoef = 0.1
specularCoef = 0.6
specularP = 256


# the camera
camera = FPSCamera()
camera.eyePos = np.array((0.0, 0.0, 5.0), np.float32)

# compute position for each key frame
frameTicks = np.linspace(0.0, 1.0, numFramePerLoop)

# get the vertex data of the sphere
sphereTriangles = uniform_tessellate_half_sphere()
sphereData = [np.concatenate([tri.vertices, tri.normals], axis=1) for tri in sphereTriangles]
sphereVertexCount = 3 * len(sphereData)
sphereData = np.asarray(sphereData).flatten().astype(np.float32)

# get the vertex data of the cylinder
cylinderTriangles = uniform_tessellate_half_cylinder()
cylinderData = [np.concatenate([tri.vertices, tri.normals], axis=1) for tri in cylinderTriangles]
cylinderVertexCount = 3 * len(cylinderData)
cylinderData = np.asarray(cylinderData).flatten().astype(np.float32)

actualPathPos = [ellipseFunc(x) for x in actualPathTicks]
actualPathPos.append(actualPathPos[0])
actualPathPos = np.asarray(actualPathPos)
pathVertexCount = actualPathPos.shape[0]
actualPathPos = actualPathPos.flatten().astype(np.float32)

def get_spherical_coord(pitch, yaw):
    return np.asarray(
        [
            np.cos(pitch) * np.cos(yaw),
            np.sin(pitch),
            np.cos(pitch) * np.sin(yaw)
        ]
    )

def debug_message_callback(source, msg_type, msg_id, severity, length, raw, user):
    msg = raw[0:length]
    print('debug', source, msg_type, msg_id, severity, msg)


# stores which keys are pressed and handle key press in the main loop
keyArray = np.array([False] * 300, np.bool)


def window_keypress_callback(theWindow, key, scanCode, action, mods):
    global useBicubic, controlId

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
    theWindow = glfw.create_window(windowSize[0], windowSize[1], 'Inverse Kinematics', None, None)
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


    sphereDataVBO = VBO(sphereData, usage='GL_STATIC_DRAW')
    sphereDataVBO.create_buffers()

    sphereVAO = glGenVertexArrays(1)

    glBindVertexArray(sphereVAO)
    sphereDataVBO.bind()
    sphereDataVBO.copy_data()
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * ctypes.sizeof(ctypes.c_float),
                          ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))
    glEnableVertexAttribArray(1)
    sphereDataVBO.unbind()
    glBindVertexArray(0)

    cylinderDataVBO = VBO(cylinderData, usage='GL_STATIC_DRAW')
    cylinderDataVBO.create_buffers()

    cylinderVAO = glGenVertexArrays(1)

    glBindVertexArray(cylinderVAO)
    cylinderDataVBO.bind()
    cylinderDataVBO.copy_data()
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * ctypes.sizeof(ctypes.c_float),
                          ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))
    glEnableVertexAttribArray(1)
    cylinderDataVBO.unbind()
    glBindVertexArray(0)

    pathVBO = VBO(actualPathPos, usage='GL_STATIC_DRAW')
    pathVBO.create_buffers()

    pathVAO = glGenVertexArrays(1)
    glBindVertexArray(pathVAO)
    pathVBO.bind()
    pathVBO.copy_data()
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    pathVBO.unbind()
    glBindVertexArray(0)

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

    lineUniformInfos = [
        ('projection', 'mat4f'),
        ('view', 'mat4f'),
        ('model', 'mat4f'),
        ('viewPos', 'vec3f'),
        ('lineWidth', 'float'),
        ('lineColor', 'vec3f')
    ]

    uniforms = create_uniform(renderProgram.get_program_id(), uniformInfos)
    lineUniforms = create_uniform(lineProgram.get_program_id(), lineUniformInfos)

    # change drawing mode
    # glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

    frameCounter = 0

    # keep rendering until the window should be closed
    while not glfw.window_should_close(theWindow):
        # set background color
        glClearColor(*windowBackgroundColor)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        aspect = windowSize[0] / windowSize[1]

        # draw the actual path first
        lineProgram.use()
        lineUniforms['projection'].update(camera.get_projection_matrix(aspect, zNear, zFar))
        lineUniforms['view'].update(camera.get_view_matrix())
        lineUniforms['model'].update(np.identity(4, np.float32))
        lineUniforms['lineWidth'].update(pathLineWidth)
        lineUniforms['viewPos'].update(camera.get_eye_pos())
        lineUniforms['lineColor'].update(pathColor)

        glBindVertexArray(pathVAO)
        glDrawArrays(GL_LINE_STRIP, 0, pathVertexCount)
        glBindVertexArray(0)

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


        # drawing the joints
        uniforms['objectColor'].update(jointColor)
        jointScaleMat = scale(jointScale, jointScale, jointScale)
        jointScaleMatFlip = scale(jointScale, jointScale, -jointScale)
        glBindVertexArray(sphereVAO)

        # draw the origin (base)
        basePos = roboticArm.origin.tolist()
        uniforms['model'].update(translate(*basePos) @ jointScaleMat)
        glDrawArrays(GL_TRIANGLES, 0, sphereVertexCount)
        # flip the sphere and render again to make it a full sphere
        uniforms['model'].update(translate(*basePos) @ jointScaleMatFlip)
        glDrawArrays(GL_TRIANGLES, 0, sphereVertexCount)

        t = frameTicks[frameCounter]
        currentPs = pFunc(t)
        currentYs = yFunc(t)
        currentSumPs = np.cumsum(currentPs)
        currentSumYs = np.cumsum(currentYs)
        armEndPos = roboticArm.get_all_arm_positions_args(roboticArm.origin, roboticArm.armLengths, currentPs, currentYs)

        # draw the end points
        for i in range(roboticArm.numSegments):
            jointPos = armEndPos[i].tolist()
            uniforms['model'].update(translate(*jointPos) @ jointScaleMat)
            glDrawArrays(GL_TRIANGLES, 0, sphereVertexCount)
            # flip the sphere and render again to make it a full sphere
            uniforms['model'].update(translate(*jointPos) @ jointScaleMatFlip)
            glDrawArrays(GL_TRIANGLES, 0, sphereVertexCount)

        glBindVertexArray(0)

        # draw the cylinders
        uniforms['objectColor'].update(cylinderColor)

        glBindVertexArray(cylinderVAO)
        for i in range(roboticArm.numSegments):
            pitch = currentSumPs[i]
            yaw = currentSumYs[i]
            armY = get_spherical_coord(pitch, yaw)
            armX = get_spherical_coord(pitch - np.pi / 2.0, yaw + np.pi / 2.0)
            armZ = normalized(np.cross(armX, armY))
            armMat = np.identity(4, np.float32)
            armMat[:3, 0] = armX
            armMat[:3, 1] = armY
            armMat[:3, 2] = armZ

            lastPos = roboticArm.origin if i == 0 else armEndPos[i - 1]
            targetArmLength = roboticArm.armLengths[i] - 2.0 * armOffset
            newPos = lastPos + armOffset * armY

            positionMat = translate(newPos[0], newPos[1], newPos[2]) @ armMat @ scale(1.0, targetArmLength, 1.0)

            uniforms['model'].update(positionMat @ scale(armScale, 1.0, armScale))
            glDrawArrays(GL_TRIANGLES, 0, cylinderVertexCount)
            uniforms['model'].update(positionMat @ scale(armScale, 1.0, -armScale))
            glDrawArrays(GL_TRIANGLES, 0, cylinderVertexCount)

        glBindVertexArray(0)


        # respond key press
        keyboard_respond_func()
        # tell glfw to poll and process window events
        glfw.poll_events()
        # swap frame buffer
        glfw.swap_buffers(theWindow)

        frameCounter = (frameCounter + 1) % numFramePerLoop

    # clean up VAO
    glDeleteVertexArrays(3, [sphereVAO, cylinderVAO, pathVAO])
    # clean up VBO
    sphereDataVBO.delete()
    cylinderDataVBO.delete()
    pathVBO.delete()
    # clean up program
    renderProgram.delete()

    # terminate glfw
    glfw.terminate()

