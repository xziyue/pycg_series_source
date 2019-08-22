import audioread
import numpy as np
import openal

audioBuffer = []

sampleRate = None
audioLength = None

soundFile = 'Jerobeam Fenderson - Planets.wav'
# open with OpenAL
alSound = openal.oalOpen(soundFile)

# load audio
with audioread.audio_open(soundFile) as inaudio:
    assert inaudio.channels == 2
    sampleRate = inaudio.samplerate
    audioLength = inaudio.duration
    for buf in inaudio:
        data = np.frombuffer(buf, dtype=np.int16)
        audioBuffer.append(data)

dataBuffer = np.concatenate(audioBuffer).reshape((-1, 2)).astype(np.float32)
numTotalSamples = dataBuffer.shape[0]
dataBuffer /= (0x7fff - 1) # max value of int16
dataBuffer = dataBuffer.flatten()


'''
# shows Lissajous curve
#tArray = np.arange(0, 1000000).astype(np.float)
tArray = np.linspace(0, 1000000, 1000000).astype(np.float)
numTotalSamples = tArray.size
x = np.sin(5.0 * tArray)
y = np.sin(4.0 * tArray)
sampleRate = 40000
audioLength = tArray.size // sampleRate
dataBuffer = np.stack([x, y], axis=1)
dataBuffer -= dataBuffer.min()
dataBuffer /= dataBuffer.max()
dataBuffer = (dataBuffer - 0.5) * 2.0
dataBuffer = dataBuffer.astype(np.float32).flatten()
'''

from OpenGL.GL import *
from OpenGL.arrays.vbo import VBO
import glfw
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
from Tutorial_8.shader import *

windowSize = (800, 600)
windowBackgroundColor = (0.2, 0.2, 0.2, 1.0)
waveColor = np.asarray([0.0, 1.0, 0.0], np.float32)

tailDuration = 0.1

numTailSamples = int(np.round(tailDuration * sampleRate))

def debug_message_callback(source, msg_type, msg_id, severity, length, raw, user):
    msg = raw[0:length]
    print('debug', source, msg_type, msg_id, severity, msg)

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
    theWindow = glfw.create_window(windowSize[0], windowSize[1], 'Audio Oscilloscope', None, None)
    # make window the current context
    glfw.make_context_current(theWindow)

    # enable z-buffer
    glEnable(GL_DEPTH_TEST)

    dataVBO = VBO(dataBuffer, usage='GL_STATIC_DRAW')

    dataVAO = glGenVertexArrays(1)

    glBindVertexArray(dataVAO)
    dataVBO.bind()
    dataVBO.copy_data()
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    dataVBO.unbind()
    glBindVertexArray(0)


    renderProgram = GLProgram(waveVertexShaderSource, waveFragmentShaderSource)
    renderProgram.compile_and_link()

    waveColorUniform = GLUniform(renderProgram.get_program_id(), 'waveColor', 'vec3f')

    # change drawing mode
    # glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

    startTime = glfw.get_time()

    soundPlayed = False

    # keep rendering until the window should be closed
    while not glfw.window_should_close(theWindow):

        nowTime = glfw.get_time()
        if nowTime - startTime > audioLength:
            glfw.set_window_should_close(theWindow, True)
            continue

        # set background color
        glClearColor(*windowBackgroundColor)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        aspect = windowSize[0] / windowSize[1]

        renderProgram.use()

        waveColorUniform.update(waveColor)

        nowLocation = min(numTotalSamples, int(np.round((nowTime - startTime) * sampleRate)))
        startLocation = max(0, nowLocation - numTailSamples)
        glBindVertexArray(dataVAO)
        glDrawArrays(GL_POINTS, startLocation, nowLocation - startLocation)
        glBindVertexArray(0)


        # tell glfw to poll and process window events
        glfw.poll_events()
        # swap frame buffer
        glfw.swap_buffers(theWindow)

        if not soundPlayed:
            alSound.play()
            soundPlayed = True

    # clean up VAO

    glDeleteVertexArrays(1, [dataVAO])
    # clean up VBO
    dataVBO.delete()
    # clean up program
    renderProgram.delete()

    # terminate glfw
    glfw.terminate()
    openal.oalQuit()
