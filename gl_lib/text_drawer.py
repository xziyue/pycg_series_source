import freetype as ft
from OpenGL.GL import *
from OpenGL.arrays.vbo import VBO
from gl_lib.utility import *
from gl_lib.transmat import orthographic_projection
import ctypes
import os

textRenderVertexShaderSource = r'''
#version 330 core
layout (location = 0) in vec4 aVec;
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
    def __init__(self, texture, glyph):
        self.texture = texture
        self.textureSize = (glyph.bitmap.width, glyph.bitmap.rows)
        self.bearing = (glyph.bitmap_left, glyph.bitmap_top)
        self.advance = glyph.advance.x


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
        self.vbo = VBO(self._get_rendering_buffer(0, 0, 0, 0))
        self.vbo.create_buffers()
        self.vboId = glGenBuffers(1)

        # initialize VAO
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vboId)
        self.vbo.bind()
        self.vbo.copy_data()

        glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 4 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        # self.vbo.unbind()
        glBindVertexArray(0)

        self.zNear = -1.0
        self.zFar = 1.0

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
            characterSlot = CharacterSlot(texture, self.face.glyph)
            self.textures[character] = characterSlot

    def get_character(self, ch):
        if ch not in self.textures:
            self.load_character(ch)
        return self.textures[ch]

    def _get_rendering_buffer(self, xpos, ypos, w, h):
        return np.asarray([
                    xpos, ypos - h, 0.0, 1.0,
                    xpos, ypos, 0.0, 0.0,
                    xpos + w, ypos, 1.0, 0.0,
                    xpos, ypos - h, 0.0, 1.0,
                    xpos + w, ypos, 1.0, 0.0,
                    xpos + w, ypos - h, 1.0, 1.0
                ], np.float32)

    def _draw_text(self, text, textPos, windowSize, scale, linespread, foreColor):
        if len(text) == 0:
            return

        blendEnabled = glIsEnabled(GL_BLEND)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.renderProgram.use()
        glBindVertexArray(self.vao)
        glActiveTexture(GL_TEXTURE0)

        foreColor = np.asarray(foreColor, np.float32)
        self.textColorUniform.update(foreColor)

        projectionMat = orthographic_projection(0.0, windowSize[0], 0.0, windowSize[1], self.zNear, self.zFar)
        self.projectionUniform.update(projectionMat)

        lineY = textPos[1]
        nowX = textPos[0]

        # split text into lines
        lines = text.split('\n')

        for line in lines:

            maxBottom = None

            if len(line) > 0:
                # analyze this line
                bearings = []
                for ch in line:
                    charSlot = self.get_character(ch)
                    bearings.append(charSlot.bearing[1] * scale)

                maxBearings = max(bearings)

                for ch in line:
                    charSlot = self.get_character(ch)

                    xpos = nowX + charSlot.bearing[0] * scale
                    yLowerd = (maxBearings - charSlot.bearing[1] * scale)
                    ypos = lineY - yLowerd

                    if maxBottom is None:
                        maxBottom = 0.0
                    maxBottom = max(maxBottom, yLowerd + charSlot.textureSize[1])

                    w = charSlot.textureSize[0] * scale
                    h = charSlot.textureSize[1] * scale

                    charSlot.texture.bind()
                    self.vbo.bind()
                    self.vbo.set_array(self._get_rendering_buffer(xpos, ypos, w, h))
                    self.vbo.copy_data()
                    self.vbo.unbind()

                    glDrawArrays(GL_TRIANGLES, 0, 6)
                    charSlot.texture.unbind()

                    # the advance is number of 1/64 pixels
                    nowX += (charSlot.advance / 64.0) * scale

            nowX = textPos[0]

            if maxBottom is None:
                # using default line spread in this case
                yOffset = self.get_character('X').textureSize[1] * scale
            else:
                yOffset = maxBottom + self.get_character('x').textureSize[1] * scale * linespread

            lineY -= yOffset

        glBindVertexArray(0)

        if not blendEnabled:
            glDisable(GL_BLEND)

    def draw_text(self, text, textPos, windowSize, color=(1.0, 1.0, 1.0), scale=1.0, linespread=-0.8):
        return self._draw_text(text, textPos, windowSize, scale, linespread, color)


class TextDrawer_Outlined:

    def __init__(self):
        self.face = None
        self.stroker = None
        self.foreTextures = []
        self.backTextures = []

        # compile rendering program
        self.renderProgram = GLProgram(textRenderVertexShaderSource, textRenderFragmentShaderSource)
        self.renderProgram.compile_and_link()

        # make projection uniform
        self.projectionUniform = GLUniform(self.renderProgram.get_program_id(), 'projection', 'mat4f')
        self.textColorUniform = GLUniform(self.renderProgram.get_program_id(), 'textColor', 'vec3f')

        # create rendering buffer
        self.vbo = VBO(self._get_rendering_buffer(0, 0, 0, 0))
        self.vbo.create_buffers()
        self.vboId = glGenBuffers(1)

        # initialize VAO
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vboId)
        self.vbo.bind()
        self.vbo.copy_data()

        glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 4 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        # self.vbo.unbind()
        glBindVertexArray(0)

        self.zNear = -1.0
        self.zFar = 1.0

    def delete(self):
        self.foreTextures.clear()
        self.backTextures.clear()
        self.face = None
        self.stroker = None
        self.renderProgram.delete()
        self.projectionUniform = None
        self.textColorUniform = None
        self.vbo.delete()
        glDeleteVertexArrays(1, [self.vao])

    def load_font(self, fontFilename, fontSize, outlineSize):
        assert os.path.exists(fontFilename)
        self.foreTextures.clear()
        self.backTextures.clear()

        self.face = ft.Face(fontFilename)
        self.face.set_char_size(fontSize)
        self.stroker = ft.Stroker()
        self.stroker.set(outlineSize, ft.FT_STROKER_LINECAPS['FT_STROKER_LINECAP_ROUND'],
                         ft.FT_STROKER_LINEJOINS['FT_STROKER_LINEJOIN_ROUND'], 0)

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

    def _get_rendering_buffer(self, xpos, ypos, w, h):
        return np.asarray([
                    xpos, ypos - h, 0.0, 1.0,
                    xpos, ypos, 0.0, 0.0,
                    xpos + w, ypos, 1.0, 0.0,
                    xpos, ypos - h, 0.0, 1.0,
                    xpos + w, ypos, 1.0, 0.0,
                    xpos + w, ypos - h, 1.0, 1.0
                ], np.float32)

    def _draw_text(self, text, textPos, windowSize, scale, linespread, foreColor):
        if len(text) == 0:
            return

        blendEnabled = glIsEnabled(GL_BLEND)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.renderProgram.use()
        glBindVertexArray(self.vao)
        glActiveTexture(GL_TEXTURE0)

        foreColor = np.asarray(foreColor, np.float32)
        self.textColorUniform.update(foreColor)

        projectionMat = orthographic_projection(0.0, windowSize[0], 0.0, windowSize[1], self.zNear, self.zFar)
        self.projectionUniform.update(projectionMat)

        lineY = textPos[1]
        nowX = textPos[0]

        # split text into lines
        lines = text.split('\n')

        for line in lines:

            maxBottom = None

            if len(line) > 0:
                # analyze this line
                bearings = []
                for ch in line:
                    charSlot = self.get_character(ch)
                    bearings.append(charSlot.bearing[1] * scale)

                maxBearings = max(bearings)

                for ch in line:
                    charSlot = self.get_character(ch)

                    xpos = nowX + charSlot.bearing[0] * scale
                    yLowerd = (maxBearings - charSlot.bearing[1] * scale)
                    ypos = lineY - yLowerd

                    if maxBottom is None:
                        maxBottom = 0.0
                    maxBottom = max(maxBottom, yLowerd + charSlot.textureSize[1])

                    w = charSlot.textureSize[0] * scale
                    h = charSlot.textureSize[1] * scale

                    charSlot.texture.bind()
                    self.vbo.bind()
                    self.vbo.set_array(self._get_rendering_buffer(xpos, ypos, w, h))
                    self.vbo.copy_data()
                    self.vbo.unbind()

                    glDrawArrays(GL_TRIANGLES, 0, 6)
                    charSlot.texture.unbind()

                    # the advance is number of 1/64 pixels
                    nowX += (charSlot.advance / 64.0) * scale

            nowX = textPos[0]

            if maxBottom is None:
                # using default line spread in this case
                yOffset = self.get_character('X').textureSize[1] * scale
            else:
                yOffset = maxBottom + self.get_character('x').textureSize[1] * scale * linespread

            lineY -= yOffset


        glBindVertexArray(0)

        if not blendEnabled:
            glDisable(GL_BLEND)

    def draw_text(self, text, textPos, windowSize, color=(1.0, 1.0, 1.0), scale=1.0, linespread=-0.8):
        return self._draw_text(text, textPos, windowSize, scale, linespread, color)