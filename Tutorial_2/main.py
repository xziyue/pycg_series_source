from OpenGL.GL import *
from OpenGL.arrays.vbo import VBO
import glfw
import numpy as np
import platform
import ctypes
from datetime import datetime

# add last folder into PYTHONPATH
import sys, os
lastFolder = os.path.split(os.getcwd())[0]
sys.path.append(lastFolder)

from gl_lib.transmat import *
from gl_lib.utility import GLUniform, GLProgram
from gl_lib.fps_camera import *
from gl_lib.gl_screenshot import save_screenshot_rgb

from misc.sphere_tessellation import uniform_tessellate_half_sphere

# program configurations
windowSize = (800, 600)
windowBackgroundColor = (0.0, 0.0, 0.0, 1.0)
zNear = 0.1
zFar = 300.0

# if using anisotropic shading
aniso = False
threadDir = normalized(np.asarray([-2.0, 1.0, -1.0], np.float32))

# lighting configurations
lightColor = np.asarray([1.0, 1.0, 1.0], np.float32)
objectColor = np.asarray([0.5, 0.3, 0.4], np.float32)
ambientCoef = 0.1
specularCoef = 0.6
specularP = 64

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
        0, 1, 2,
        0, 2, 3,
        1, 5, 6,
        1, 6, 2,
        2, 6, 7,
        2, 7, 3,
        3, 7, 4,
        3, 4, 0,
        0, 4, 5,
        0, 5, 1,
        4, 6, 5,
        4, 7, 6
    ]
    , np.uint32
)

# compute normal for each surface and form a new array
tempArray = []
tempVertices = vertices.reshape((-1, 3))
for i in range(0, elements.size, 3):
    triVertices = tempVertices[elements[i: i + 3]]
    normal = normalized(np.cross(triVertices[1] - triVertices[0], triVertices[2] - triVertices[0]))
    for j in range(3):
        tempArray.append(np.concatenate([triVertices[j], normal]))

cubeVertexCount = len(tempArray)
cubeData = np.asarray(tempArray, np.float32).flatten()

# get the vertex data of the sphere
sphereTriangles = uniform_tessellate_half_sphere()
sphereData = [np.concatenate([tri.vertices, tri.normals], axis=1) for tri in sphereTriangles]
sphereVertexCount = 3 * len(sphereData)
sphereData = np.asarray(sphereData).flatten().astype(np.float32)


vertexShaderSource = r'''
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

out vec3 fragPos;
out vec3 bNormal;

void main()
{
    fragPos = vec3(model * vec4(aPos, 1.0));
    bNormal = mat3(transpose(inverse(model))) * aNormal;
    gl_Position = projection * view * model * vec4(aPos, 1.0);
}
'''

fragmentShaderSource = r'''
#version 330 core
in vec3 fragPos;
in vec3 bNormal;
out vec4 fragColor;

uniform vec3 objectColor;
uniform vec3 lightColor;
uniform vec3 viewPos;
uniform vec3 lightPos;
uniform float ambientCoef;
uniform float specularCoef;
uniform int specularP;

void main()
{   
    vec3 cNormal = normalize(bNormal);
    vec3 ambient = ambientCoef * lightColor;
    
    vec3 lightDir = normalize(lightPos - fragPos);
    float diffMul = max(0.0, dot(cNormal, lightDir));
    vec3 diffuse = diffMul * lightColor;
    
    vec3 viewDir = normalize(viewPos - fragPos);
    vec3 reflectDir = normalize(reflect(-lightDir, cNormal));
    float specMul = pow(max(0.0, dot(viewDir, reflectDir)), specularP);
    vec3 specular = specMul * specularCoef * lightColor;
    
    vec3 result = (ambient + diffuse + specular) * objectColor;
    fragColor = vec4(result, 1.0);
}
'''

anisoFragmentShaderSource = r'''
#version 330 core
in vec3 fragPos;
in vec3 bNormal;
out vec4 fragColor;

uniform vec3 objectColor;
uniform vec3 lightColor;
uniform vec3 viewPos;
uniform vec3 lightPos;
uniform float ambientCoef;
uniform float specularCoef;
uniform int specularP;
uniform vec3 threadDir;

void main()
{   
    vec3 cNormal = normalize(bNormal);
    vec3 ambient = ambientCoef * lightColor;
    
    vec3 t = normalize(threadDir - dot(threadDir, cNormal) * cNormal);
    vec3 lightDir = normalize(lightPos - fragPos);
    vec3 viewDir = normalize(viewPos - fragPos);
    
    float dotlt = dot(lightDir, t);
    float dotvt = dot(viewDir, t);
    
    float diffMul = sqrt(1.0 - pow(dotlt, 2));
    vec3 diffuse = diffMul * lightColor;
    
    float specMul = sqrt(1.0 - pow(dotlt, 2)) * sqrt(1.0 - pow(dotvt, 2)) - dotlt * dotvt;
    specMul = pow(max(0.0, specMul), specularP);
    vec3 specular = specMul * specularCoef * lightColor;

    vec3 result = (ambient + diffuse + specular) * objectColor;
    fragColor = vec4(result, 1.0);
}
'''

cursorPos = None


def debug_message_callback(source, msg_type, msg_id, severity, length, raw, user):
    msg = raw[0:length]
    print('debug', source, msg_type, msg_id, severity, msg)


# stores which keys are pressed and handle key press in the main loop
keyArray = np.array([False] * 300, np.bool)


def window_keypress_callback(theWindow, key, scanCode, action, mods):
    global aniso

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
            aniso = not aniso
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


if __name__ == '__main__':

    # initialize glfw
    glfw.init()

    # set glfw config
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    if platform.system().lower() == 'darwin':
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
    # glfw.set_framebuffer_size_callback(theWindow, window_resize_callback)

    glfw.set_key_callback(theWindow, window_keypress_callback)
    # disable cursor
    glfw.set_input_mode(theWindow, glfw.CURSOR, glfw.CURSOR_DISABLED)

    glfw.set_cursor_pos_callback(theWindow, window_cursor_callback)
    # initialize cursor position
    cursorPos = glfw.get_cursor_pos(theWindow)

    glfw.set_scroll_callback(theWindow, window_scroll_callback)

    # create VBOs to store vertices, normals and elements
    cubeDataVBO = VBO(cubeData, usage='GL_STATIC_DRAW')
    cubeDataVBO.create_buffers()

    sphereDataVBO = VBO(sphereData, usage='GL_STATIC_DRAW')
    sphereDataVBO.create_buffers()

    # create VAO to describe array information
    triangleVAO, sphereVAO = glGenVertexArrays(2)

    # bind VAO
    glBindVertexArray(triangleVAO)
    # bind data VBO
    cubeDataVBO.bind()
    cubeDataVBO.copy_data()
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * ctypes.sizeof(ctypes.c_float),
                          ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))
    glEnableVertexAttribArray(1)
    # unbind VBO
    cubeDataVBO.unbind()
    # unbind VAO
    glBindVertexArray(0)

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

    renderProgram = GLProgram(vertexShaderSource, fragmentShaderSource)
    renderProgram.compile_and_link()
    anisoRenderProgram = GLProgram(vertexShaderSource, anisoFragmentShaderSource)
    anisoRenderProgram.compile_and_link()

    # create uniforms
    renderProgramUniforms = {
        'projection': GLUniform(renderProgram.get_program_id(), 'projection', 'mat4f'),
        'view': GLUniform(renderProgram.get_program_id(), 'view', 'mat4f'),
        'model': GLUniform(renderProgram.get_program_id(), 'model', 'mat4f'),
        'lightPos': GLUniform(renderProgram.get_program_id(), 'lightPos', 'vec3f'),
        'viewPos': GLUniform(renderProgram.get_program_id(), 'viewPos', 'vec3f'),
        'lightColor': GLUniform(renderProgram.get_program_id(), 'lightColor', 'vec3f'),
        'objectColor': GLUniform(renderProgram.get_program_id(), 'objectColor', 'vec3f'),
        'ambientCoef': GLUniform(renderProgram.get_program_id(), 'ambientCoef', 'float'),
        'specularCoef': GLUniform(renderProgram.get_program_id(), 'specularCoef', 'float'),
        'specularP': GLUniform(renderProgram.get_program_id(), 'specularP', 'int')
    }
    
    anisoRenderProgramUniforms = {
        'projection': GLUniform(anisoRenderProgram.get_program_id(), 'projection', 'mat4f'),
        'view': GLUniform(anisoRenderProgram.get_program_id(), 'view', 'mat4f'),
        'model': GLUniform(anisoRenderProgram.get_program_id(), 'model', 'mat4f'),
        'lightPos': GLUniform(anisoRenderProgram.get_program_id(), 'lightPos', 'vec3f'),
        'viewPos': GLUniform(anisoRenderProgram.get_program_id(), 'viewPos', 'vec3f'),
        'lightColor': GLUniform(anisoRenderProgram.get_program_id(), 'lightColor', 'vec3f'),
        'objectColor': GLUniform(anisoRenderProgram.get_program_id(), 'objectColor', 'vec3f'),
        'ambientCoef': GLUniform(anisoRenderProgram.get_program_id(), 'ambientCoef', 'float'),
        'specularCoef': GLUniform(anisoRenderProgram.get_program_id(), 'specularCoef', 'float'),
        'specularP': GLUniform(anisoRenderProgram.get_program_id(), 'specularP', 'int'),
        'threadDir' : GLUniform(anisoRenderProgram.get_program_id(), 'threadDir', 'vec3f')
    }

    uniforms = renderProgramUniforms

    # change drawing mode
    # glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

    rotateDegree = 0.0

    # keep rendering until the window should be closed
    while not glfw.window_should_close(theWindow):
        # set background color
        glClearColor(*windowBackgroundColor)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if aniso:
            anisoRenderProgram.use()
            uniforms = anisoRenderProgramUniforms
        else:
            renderProgram.use()
            uniforms = renderProgramUniforms

        # update shading related uniforms
        uniforms['viewPos'].update(camera.get_eye_pos())
        uniforms['lightPos'].update(camera.get_eye_pos())
        uniforms['lightColor'].update(lightColor)
        uniforms['objectColor'].update(objectColor)
        uniforms['ambientCoef'].update(ambientCoef)
        uniforms['specularCoef'].update(specularCoef)
        uniforms['specularP'].update(specularP)
        # update transformation related uniforms
        aspect = windowSize[0] / windowSize[1]
        uniforms['projection'].update(camera.get_projection_matrix(aspect, zNear, zFar))
        uniforms['view'].update(camera.get_view_matrix())


        # generate a rotating animation
        uniforms['model'].update(translate(-1, 0, 0) @ rotate(unit_z(), rotateDegree, True))

        if aniso:
            # update rotated thread direction
            uniforms['threadDir'].update(rotate(unit_z(), rotateDegree, True)[:3, :3] @ threadDir)

        # drawing the cube
        rotateDegree += 1.0
        # bind VAO
        glBindVertexArray(triangleVAO)
        # draw vertices
        glDrawArrays(GL_TRIANGLES, 0, cubeVertexCount)
        # unbind VAO
        glBindVertexArray(0)

        # drawing the sphere
        # update shading related uniforms
        uniforms['viewPos'].update(camera.get_eye_pos())
        uniforms['lightPos'].update(camera.get_eye_pos())
        uniforms['lightColor'].update(lightColor)
        uniforms['objectColor'].update(objectColor)
        uniforms['ambientCoef'].update(ambientCoef)
        uniforms['specularCoef'].update(specularCoef)
        uniforms['specularP'].update(specularP)
        # update transformation related uniforms
        aspect = windowSize[0] / windowSize[1]
        uniforms['projection'].update(camera.get_projection_matrix(aspect, zNear, zFar))
        uniforms['view'].update(camera.get_view_matrix())
        uniforms['model'].update(translate(1.5, 0, -1))

        if aniso:
            # update rotated thread direction
            uniforms['threadDir'].update(threadDir)

        glBindVertexArray(sphereVAO)
        glDrawArrays(GL_TRIANGLES, 0, sphereVertexCount)
        # flip the sphere and render again to make it a full sphere
        uniforms['model'].update(translate(1.5, 0, -1) @ scale(1, 1, -1))
        glDrawArrays(GL_TRIANGLES, 0, sphereVertexCount)
        glBindVertexArray(0)

        # respond key press
        keyboard_respond_func()
        # tell glfw to poll and process window events
        glfw.poll_events()
        # swap frame buffer
        glfw.swap_buffers(theWindow)


    # clean up VAO
    glDeleteVertexArrays(2, [triangleVAO, sphereVAO])
    # clean up VBO
    cubeDataVBO.delete()
    sphereDataVBO.delete()
    # clean up program
    renderProgram.delete()

    # terminate glfw
    glfw.terminate()
