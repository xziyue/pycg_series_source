import freetype as ft
from OpenGL.GL import *
from OpenGL.arrays.vbo import VBO
from gl_lib.utility import *
from gl_lib.transmat import orthographic_projection
import ctypes
import os

textRenderVertexShaderSource = r'''
#version 330 core
layout (location = 1) in vec4 aVec;
out vec2 bTexPos;

uniform mat4 projection;

void main()
{
    gl_Position = projection * vec4(aVec.xy, 0.0, 1.0);
    bTexPos = aVec.zw;
}  
'''

textRenderFragmentShaderSource = r'''
#version 330 core
in vec2 bTexPos;
out vec4 color;

uniform vec3 textColor;
uniform sampler2D textureSample;

void main()
{
    vec4 sampled = vec4(1.0, 1.0, 1.0, texture(textureSample, bTexPos).r);
    color = vec4(textColor, 1.0) * sampled;
}  
'''

class CharacterSlot:
    def __init__(self):
        self.texture = None
        self.textureSize = None
        self.bearing = None
        self.advance = None

class TextDrawer:

    def __init__(self):
        self.face = None
        self.textures = dict()

        # compile rendering program
        self.renderProgram = GLProgram(textRenderVertexShaderSource, textRenderFragmentShaderSource)
        self.renderProgram.compile_and_link()

        # make projection uniform
        self.projectionUniform = GLUniform(self.renderProgram.get_program_id(), 'projection', 'mat4f')
        self.textColorUniform = GLUniform(self.renderProgram.get_program_id(), 'textColor', 'vec3f')

        # create rendering buffer
        self.renderingBuffer = np.zeros(24, np.float32)
        self.vbo = VBO(self.renderingBuffer)
        self.vbo.create_buffers()

        # initialize VAO
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        self.vbo.bind()
        self.vbo.copy_data()
        glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 4 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        self.vbo.unbind()
        glBindVertexArray(0)

        self.zNear = 0.02
        self.zFar = 10.0

    def delete(self):
        self.textures.clear()
        self.face = None
        self.renderProgram.delete()
        self.projectionUniform = None
        self.textColorUniform = None
        self.vbo.delete()
        glDeleteVertexArrays(1, [self.vao])

    def load_font(self, fontFilename, fontSize):
        assert os.path.exists(fontFilename)
        self.textures.clear()

        self.face = ft.Face(fontFilename)
        self.face.set_char_size(fontSize)

        # load all ASCII characters
        for i in range(128):
            self.load_character(chr(i))

    def load_character(self, character):
        assert self.face is not None
        assert len(character) == 1

        if character not in self.textures:
            # load glyph in freetype
            self.face.load_char(character)
            ftBitmap = self.face.glyph.bitmap
            height, width = ftBitmap.rows, ftBitmap.width
            bitmap = np.array(ftBitmap.buffer, dtype=np.uint8)

            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            texture = GLTexture2D()
            texture.bind()

            # pass texture data
            glTexImage2D(
                GL_TEXTURE_2D,
                0,
                GL_RED,
                width,
                height,
                0,
                GL_RED,
                GL_UNSIGNED_BYTE,
                get_numpy_unit8_array_pointer(bitmap)
            )

            # set texture options
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

            texture.unbind()

            # add texture object to the dictionary
            characterSlot = CharacterSlot()
            characterSlot.texture = texture
            characterSlot.textureSize = (width, height)
            characterSlot.bearing = (self.face.glyph.bitmap_left, self.face.glyph.bitmap_top)
            characterSlot.advance = self.face.glyph.advance.x
            self.textures[character] = characterSlot

    def get_character(self, ch):
        if ch not in self.textures:
            self.load_character(ch)
        return self.textures[ch]

    def draw_text(self, text, textPos, windowSize, color = (1.0, 1.0, 1.0), scale = 1.0, linespread = 1.1):
        if len(text) == 0:
            return

        ifBlend = glIsEnabled(GL_BLEND)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.renderProgram.use()
        glBindVertexArray(self.vao)
        glActiveTexture(GL_TEXTURE0)

        color = np.asarray(color, np.float32)
        self.textColorUniform.update(color)

        projectionMat = orthographic_projection(0.0, windowSize[0], 0.0, windowSize[1], self.zNear, self.zFar)
        self.projectionUniform.update(projectionMat)

        lineY = textPos[1]
        nowX = textPos[0]

        for ch in text:
            if ch == '\n':
                nowX = textPos[0]
                # the line spacing is computed according to character 'X'
                lineY -= self.get_character('X').textureSize[1] * scale * linespread
            else:
                charSlot = self.get_character(ch)

                xpos = nowX + charSlot.bearing[0] * scale
                ypos = lineY - (charSlot.textureSize[1] - charSlot.bearing[1]) * scale

                w = charSlot.textureSize[0] * scale
                h = charSlot.textureSize[1] * scale

                self.renderingBuffer[:] = [
                    xpos, ypos + h, 0.0, 0.0,
                    xpos, ypos, 0.0, 1.0,
                    xpos + w, ypos, 1.0, 1.0,
                    xpos, ypos + h, 0.0, 0.0,
                    xpos + w, ypos, 1.0, 1.0,
                    xpos + w, ypos + h, 1.0, 0.0
                ]

                charSlot.texture.bind()
                self.vbo.bind()
                self.vbo.set_array(self.renderingBuffer)
                self.vbo.copy_data()
                self.vbo.unbind()

                glDrawArrays(GL_TRIANGLES, 0, 6)
                charSlot.texture.unbind()
                nowX += (charSlot.advance * 64.0) * scale


        glBindVertexArray(0)

        if not ifBlend:
            glDisable(GL_BLEND)






