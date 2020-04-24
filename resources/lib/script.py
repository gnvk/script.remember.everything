# -*- coding: utf-8 -*-

from datetime import datetime,  timedelta
import logging
import os
import random
import requests
import threading
import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import kodiutils
from resources.lib import kodilogging
from resources.lib import sheet


ADDON = xbmcaddon.Addon()
CWD = ADDON.getAddonInfo('path').decode('utf-8')


logger = logging.getLogger(ADDON.getAddonInfo('id'))


class GUI(xbmcgui.WindowXML):
    def onInit(self):
        self.mid_label = self.getControl(1)
        self.score_row = self.getControl(30)
        self.highlight = self.getControl(31)

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
            self.set_mid_label(
                'Could not fetch the given Google sheet. Error: {}'.format(se.message))
        else:
            self.idx = 0
            self.show_question()
        finally:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

    @property
    def score(self):
        """
        5 - perfect response
        4 - correct response after a hesitation
        3 - correct response recalled with serious difficulty
        2 - incorrect response; where the correct one seemed easy to recall
        1 - incorrect response; the correct one remembered
        0 - complete blackout
        """
        return self._score

    @score.setter
    def score(self, score):
        self._score = max(0, min(5, score))
        self.highlight.setPosition(320 * self._score, 0)

    @property
    def answer_shown(self):
        return self._answer_shown

    @answer_shown.setter
    def answer_shown(self, v):
        self._answer_shown = v
        self.score_row.setVisible(self._answer_shown)

    def show_question(self):
        self.answer_shown = False

        if self.idx >= len(self.cards):
            self.set_mid_label(kodiutils.get_string(32100))
            return

        card = self.cards[self.idx]
        self.set_mid_label(card.question)

    def show_answer(self):
        self.answer_shown = True

        card = self.cards[self.idx]
        self.set_mid_label(card.answer)
        self.score = 3

    def update_current_card(self):
        card = self.cards[self.idx]

        if self.score < 3:
            card.streak = 0
        else:
            card.streak += 1
        card.easiness = max(
            1.3,  card.easiness + 0.1 - (5.0 - self.score) * (0.08 + (5.0 - self.score) * 0.02))
        if card.streak == 0:
            card.interval = 0
        elif card.streak == 1:
            card.interval = 1
        elif card.streak == 2:
            card.interval = 6
        else:
            card.interval = card.interval * card.easiness

        if not card.first_practice:
            card.first_practice = datetime.now().isoformat()
        card.next_practice = (datetime.now() + timedelta(days=card.interval)).isoformat()

        threading.Thread(target=self.update_card, args=(card,)).start()

    def update_card(self, card):
        try:
            self.sheet.update_card(card)
        except sheet.SheetError as se:
            logger.warning(se.message)
            cmd = 'Notification(Error, ' + \
                'Could not update the question, 3000, {}/resources/icon.png)'.format(CWD)
            xbmc.executebuiltin(cmd)

    def set_mid_label(self, text):
        self.mid_label.setLabel(text)  # pylint:disable=no-member


def show_ui():
    ui = GUI('main-window.xml', CWD, 'default', '1080i', False)
    ui.doModal()
    del ui
