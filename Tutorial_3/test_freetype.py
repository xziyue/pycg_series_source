import numpy as np
import freetype as ft
import matplotlib.pyplot as plt
import ctypes


face = ft.Face('../misc/STIX2Text-Regular.otf')
face.set_char_size(48 * 64)

face.load_char('A')

stroker = ft.FT_Stroker()
ft.FT_Stroker_Set(stroker, 2 * 64, ft.FT_STROKER_LINECAPS['FT_STROKER_LINECAP_ROUND'],
                         ft.FT_STROKER_LINEJOINS['FT_STROKER_LINEJOIN_ROUND'], 0)

glyph = face._FT_Face.contents.glyph
newGlyph = ft.FT_Glyph()
ftGlyph = ft.FT_Get_Glyph(glyph, newGlyph)
ft.FT_Glyph_StrokeBorder(newGlyph, stroker, False, True)
ft.FT_Glyph_To_Bitmap(newGlyph, ft.FT_RENDER_MODES['FT_RENDER_MODE_NORMAL'], None, True)

newGlyph = ctypes.cast(newGlyph, ft.FT_BitmapGlyph)



plt.imshow(newGlyph.bitmap)
plt.show()

