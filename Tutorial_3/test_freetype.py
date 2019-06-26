import numpy as np
import freetype as ft
import matplotlib.pyplot as plt

face = ft.Face('../misc/STIX2Text-Regular.otf')
face.set_char_size(48 * 64)

face.load_char('A')

ftBitmap = face.glyph.bitmap
bitmap = np.array(ftBitmap.buffer, np.uint8).reshape(
    (ftBitmap.rows, ftBitmap.width)
)

plt.imshow(bitmap)
plt.show()

