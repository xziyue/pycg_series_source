import numpy as np
import freetype as ft
import matplotlib.pyplot as plt
import ctypes

class FT_BitmapGlyphRec(ft.Structure):

    _fields_ = [
        ('root', ft.FT_GlyphRec),
        ('left', ft.FT_Int),
        ('top', ft.FT_Int),
        ('bitmap', ft.FT_Bitmap)
    ]

FT_BitmapGlyph = ft.POINTER(FT_BitmapGlyphRec)

face = ft.Face('../misc/STIX2Text-Regular.otf')
face.set_char_size(60 * 64)

face.load_char('A', ft.FT_LOAD_FLAGS['FT_LOAD_DEFAULT'])

stroker = ft.Stroker()
stroker.set(2 * 64, ft.FT_STROKER_LINECAPS['FT_STROKER_LINECAP_ROUND'],
                         ft.FT_STROKER_LINEJOINS['FT_STROKER_LINEJOIN_ROUND'], 0)
glyph = ft.FT_Glyph()
ft.FT_Get_Glyph(face.glyph._FT_GlyphSlot, ft.byref(glyph))
pyGlyph = ft.Glyph(glyph)


bitmapGlyph = pyGlyph.to_bitmap(ft.FT_RENDER_MODES['FT_RENDER_MODE_NORMAL'], 0)
plt.subplot(121)
plt.imshow(np.asarray(bitmapGlyph.bitmap.buffer).reshape(bitmapGlyph.bitmap.rows, bitmapGlyph.bitmap.width))

glyph = ft.FT_Glyph()
ft.FT_Get_Glyph(face.glyph._FT_GlyphSlot, ft.byref(glyph))
pyGlyph = ft.Glyph(glyph)
error = ft.FT_Glyph_StrokeBorder(ft.byref(pyGlyph._FT_Glyph), stroker._FT_Stroker, False, False)
if error: raise ft.FT_Exception( error )
bitmapGlyph = pyGlyph.to_bitmap(ft.FT_RENDER_MODES['FT_RENDER_MODE_NORMAL'], 0)

plt.subplot(122)
plt.imshow(np.asarray(bitmapGlyph.bitmap.buffer).reshape(bitmapGlyph.bitmap.rows, bitmapGlyph.bitmap.width))
plt.show()

print('pause')
'''
glyph = ft.FT_Glyph()
ft.FT_Get_Glyph(face.glyph._FT_GlyphSlot, ft.byref(glyph))


error = ft.FT_Glyph_StrokeBorder(ft.byref(glyph), stroker._FT_Stroker, False, False)
if error:
    raise ft.FT_Exception(error)
bitmapGlyph = newGlyph.to_bitmap(ft.FT_RENDER_MODES['FT_RENDER_MODE_NORMAL'], 0)

plt.imshow(bitmapGlyph.bitmap.buffer)
plt.show()
'''

