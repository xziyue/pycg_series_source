from PIL import Image
from OpenGL.GL import *
import numpy as np

def save_screenshot_rgb(filename, windowShape):
    array = np.zeros((windowShape[1], windowShape[0], 3), np.uint8)
    glReadPixels(0, 0, windowShape[0], windowShape[1], GL_RGB, GL_UNSIGNED_BYTE, array=array)
    pilImg = Image.fromarray(array)
    pilImg = pilImg.transpose(Image.FLIP_TOP_BOTTOM)
    pilImg.save(filename)