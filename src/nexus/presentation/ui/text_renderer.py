from OpenGL.GL import *
from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = ("segoeuib.ttf", "arialbd.ttf", "arial.ttf", "segoeui.ttf")

class TextRenderer:
    def __init__(self):
        self._cache = {}
        self._fonts = {}

    def _font(self, size):
        if size not in self._fonts:
            font = None
            for name in _FONT_CANDIDATES:
                try:
                    font = ImageFont.truetype(name, size)
                    break
                except Exception:
                    continue
            if font is None:
                font = ImageFont.load_default()
            self._fonts[size] = font
        return self._fonts[size]

    def get(self, text, size=24, color=(1.0, 1.0, 1.0, 1.0)):
        text = str(text)
        key = (text, size, color)
        if key in self._cache:
            return self._cache[key]

        font = self._font(size)

        measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox = measure.textbbox((0, 0), text, font=font)
        tw = max(1, bbox[2] - bbox[0])
        th = max(1, bbox[3] - bbox[1])

        pad = 4
        img = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        rgba = tuple(int(max(0.0, min(1.0, c)) * 255) for c in color)
        draw.text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=rgba)

        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        data = img.tobytes()

        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA8, img.width, img.height, 0,
            GL_RGBA, GL_UNSIGNED_BYTE, data,
        )
        glBindTexture(GL_TEXTURE_2D, 0)

        result = (tex, img.width, img.height)
        self._cache[key] = result
        return result
