from collections import namedtuple
import mimetypes
import os
from PIL import Image
import requests
import shutil
from time import sleep

from . import IMG_DIR


SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
MAX_WIDTH = 1400.0
MAX_HEIGHT = 700.0


class Picture(object):
    def __init__(self, path, x, y, width, height):
        self.path = path
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __str__(self):
        return '{} x: {} y: {} width: {} height: {}'.format(
            self.path, self.x, self.y, self.width, self.height)


class PictureError(Exception):
    pass


def download_picture(url, name):
    # type: (str, str) -> None
    path = _get_picture_path(name)
    if os.path.exists(path):
        return
    resp = requests.get(url, stream=True)
    if not resp.ok:
        raise PictureError(resp.text)
    dir_ = os.path.dirname(path)
    if not os.path.exists(dir_):
        os.mkdir(dir_)
    with open(path, 'wb') as out_file:
        shutil.copyfileobj(resp.raw, out_file)


def _get_picture_path(name):
    return os.path.join(IMG_DIR, name)


def _get_image_with_retry(path):
    limit = 30
    for i in range(limit):
        try:
            return Image.open(path)
        except IOError:
            sleep(0.1)
            if i == limit - 1:
                raise


def get_picture(name):
    # type: (str) -> Picture
    path = _get_picture_path(name)
    try:
        image = _get_image_with_retry(path)
    except IOError as e:
        raise PictureError(e.message)
    width, height = image.size
    if width > MAX_WIDTH:
        height *= (MAX_WIDTH / width)
        width *= (MAX_WIDTH / width)
    if height > MAX_HEIGHT:
        width *= (MAX_HEIGHT / height)
        height *= (MAX_HEIGHT / height)
    x = SCREEN_WIDTH / 2 - width / 2
    y = SCREEN_HEIGHT / 2 - height / 2
    return Picture(path, int(x), int(y), int(width), int(height))
