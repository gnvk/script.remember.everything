import os
import xbmc

DATA_DIR = xbmc.translatePath(
    'special://profile/addon_data/script.remember.everything')
if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)
