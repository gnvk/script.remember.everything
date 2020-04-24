import os
import xbmc

DATA_DIR = xbmc.translatePath('special://profile/addon_data/script.remember.everything')
IMG_DIR = os.path.join(DATA_DIR, 'img')
if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)
if not os.path.exists(IMG_DIR):
    os.mkdir(IMG_DIR)
