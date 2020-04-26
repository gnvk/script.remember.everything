# -*- coding: utf-8 -*-

from datetime import datetime,  timedelta
import logging
import os
import random
import requests
import shutil
import threading
import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import card
from resources.lib import kodiutils
from resources.lib import kodilogging
from resources.lib import sheet
from resources.lib import pictures


ADDON = xbmcaddon.Addon()
CWD = ADDON.getAddonInfo('path').decode('utf-8')


logger = logging.getLogger(ADDON.getAddonInfo('id'))


class GUI(xbmcgui.WindowXML):
    def onInit(self):
        self.mid_label = self.getControl(1)
        self.progress_label = self.getControl(2)
        self.picture = self.getControl(3)
        self.score_row = self.getControl(30)
        self.highlight = self.getControl(31)
        self.score_label = self.getControl(32)

        self.answer_shown = False
        self.score = 3

        while True:
            client_id = kodiutils.get_setting('client_id')
            client_secret = kodiutils.get_setting('client_secret')
            sheet_id = kodiutils.get_setting('sheet_id')
            if client_id and client_secret and sheet_id:
                break
            xbmcgui.Dialog().ok('Error', 'Missing settings')
            kodiutils.show_settings()

        self.sheet = sheet.GoogleSheets(client_id, client_secret, sheet_id)

        self.start_game()

    def onAction(self, action):
        if action.getId() == xbmcgui.ACTION_MOVE_LEFT:
            if self.answer_shown:
                self.score -= 1
        elif action.getId() == xbmcgui.ACTION_MOVE_RIGHT:
            if self.answer_shown:
                self.score += 1
        elif action.getId() == xbmcgui.ACTION_MOVE_UP:
            pass
        elif action.getId() == xbmcgui.ACTION_MOVE_DOWN:
            pass
        elif action.getId() == xbmcgui.ACTION_SELECT_ITEM:
            if self.idx >= len(self.cards):
                return
            if self.answer_shown:
                self.update_current_card()
                self.idx += 1
                self.show_question()
            else:
                self.show_answer()
        else:
            super(GUI, self).onAction(action)

    def start_game(self):
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        try:
            self.cards = [
                card
                for card in self.sheet.get_cards()
                if card.next_practice < datetime.now().isoformat()
            ]
            random.shuffle(self.cards)
        except sheet.SheetError as se:
            self.set_label(self.mid_label,
                           'Could not fetch the given Google sheet. Error: {}'.format(se.message))
        else:
            self.idx = 0
            threading.Thread(target=self.download_pictures).start()
            self.show_question()
        finally:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

    def download_pictures(self):
        picture_urls = [
            (card.question_picture, 'q{}'.format(card.idx))
            for card in self.cards
            if card.question_picture
        ] + [
            (card.answer_picture, 'a{}'.format(card.idx))
            for card in self.cards
            if card.answer_picture
        ]
        for picture_url, name in picture_urls:
            pictures.download_picture(picture_url, name)

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, score):
        self._score = max(0, min(5, score))
        self.highlight.setPosition(320 * self.score, 0)
        self.set_label(self.score_label, card.scores[self.score])

    @property
    def answer_shown(self):
        return self._answer_shown

    @answer_shown.setter
    def answer_shown(self, v):
        self._answer_shown = v
        self.score_row.setVisible(self._answer_shown)

    def show_question(self):
        self.answer_shown = False
        self.picture.setVisible(False)
        self.update_progress_label()

        if self.idx >= len(self.cards):
            self.mid_label.setPosition(0, 500)
            self.set_label(self.mid_label, kodiutils.get_string(32100))
            return

        card = self.cards[self.idx]
        self.set_label(self.mid_label, card.question)
        if card.question_picture:
            self.show_picture('q{}'.format(card.idx))
        else:
            self.hide_picture()

    def show_answer(self):
        self.answer_shown = True
        self.picture.setVisible(False)

        card = self.cards[self.idx]
        self.set_label(self.mid_label, card.answer)
        self.score = 3
        if card.answer_picture:
            self.show_picture('a{}'.format(card.idx))
        else:
            self.hide_picture()

    def show_picture(self, name):
        self.mid_label.setPosition(0, 64)
        try:
            picture = pictures.get_picture(name)
            self.picture.setImage(picture.path)  # pylint:disable=no-member
            self.picture.setPosition(picture.x, picture.y)
            self.picture.setWidth(picture.width)
            self.picture.setHeight(picture.height)
            self.picture.setVisible(True)
        except pictures.PictureError as e:
            self.show_notification('Cannot show image: ' + e.message)

    def hide_picture(self):
        self.picture.setVisible(False)
        self.mid_label.setPosition(0, 500)

    def update_current_card(self):
        card = self.cards[self.idx]
        card.update(self.score)
        threading.Thread(target=self.update_card, args=(card,)).start()

    def update_card(self, card):
        try:
            self.sheet.update_card(card)
        except sheet.SheetError as se:
            logger.warning(se.message)
            self.show_notification('Could not update the question')

    def update_progress_label(self):
        text = '{} / {} '.format(self.idx + 1, len(self.cards)) \
            if self.idx < len(self.cards) else ''
        self.set_label(self.progress_label, text)

    @staticmethod
    def set_label(control, text):
        control.setLabel(text)

    @staticmethod
    def show_notification(text):
        xbmc.log(text, level=xbmc.LOGWARNING)
        cmd = 'Notification(Remember Everything!, {}, 5000, {}/resources/icon.png)'.format(
            text, CWD)
        xbmc.executebuiltin(cmd)


def show_ui():
    show_error = GUI('main-window.xml', CWD, 'default', '1080i', False)
    show_error.doModal()
    del show_error
