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


class MainWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        self.sheet = kwargs['sheet']
        self.selected_sheet = kwargs['selected_sheet']

    def onInit(self):
        self.mid_label = self.getControl(1)
        self.progress_label = self.getControl(2)
        self.picture = self.getControl(3)
        self.score_row = self.getControl(30)
        self.highlight = self.getControl(31)
        self.score_label = self.getControl(32)

        self.answer_shown = False
        self.score_row.setPosition(0, 1016)  # hack, see comment in the XML
        self.score = 3

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
            super(MainWindow, self).onAction(action)

    def start_game(self):
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        try:
            self.cards = [
                card
                for card in self.sheet.get_cards(self.selected_sheet)
                if card.next_practice < datetime.now().isoformat()
            ]
            random.shuffle(self.cards)
        except sheet.SheetError as se:
            set_label(self.mid_label,
                'Could not fetch the given Google sheet. Error: {}'.format(se.message))
        else:
            self.idx = 0
            self.download_pictures()
            self.show_question()
        finally:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

    def download_pictures(self):
        picture_urls = [
            (card.question_picture, '{}/q{}'.format(self.selected_sheet, card.idx))
            for card in self.cards
            if card.question_picture
        ] + [
            (card.answer_picture, '{}/a{}'.format(self.selected_sheet, card.idx))
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
        set_label(self.score_label, card.scores[self.score])

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
            set_label(self.mid_label, kodiutils.get_string(32100))
            return

        card = self.cards[self.idx]
        set_label(self.mid_label, card.question)
        if card.question_picture:
            self.show_picture('{}/q{}'.format(self.selected_sheet, card.idx))
        else:
            self.hide_picture()

    def show_answer(self):
        self.answer_shown = True
        self.picture.setVisible(False)

        card = self.cards[self.idx]
        set_label(self.mid_label, card.answer)
        self.score = 3
        if card.answer_picture:
            self.show_picture('{}/a{}'.format(self.selected_sheet, card.idx))
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
            show_notification('Cannot show image: ' + e.message)

    def hide_picture(self):
        self.picture.setVisible(False)
        self.mid_label.setPosition(0, 500)

    def update_current_card(self):
        card = self.cards[self.idx]
        card.update(self.score)
        threading.Thread(target=self.update_card, args=(card,)).start()

    def update_card(self, card):
        try:
            self.sheet.update_card(self.selected_sheet, card)
        except sheet.SheetError as se:
            logger.warning(se.message)
            show_notification('Could not update the question')

    def update_progress_label(self):
        text = '{} / {} '.format(self.idx + 1, len(self.cards)) \
            if self.idx < len(self.cards) else ''
        set_label(self.progress_label, text)


class SelectSheetWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        self.sheet = kwargs['sheet']
        self.sheet_names = []

    def onInit(self):
        self.mid_label = self.getControl(1)

        xbmc.executebuiltin('Container.SetViewMode(50)')
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        self.clearList()

        try:
            self.sheet_names = self.sheet.get_sheet_names()
        except sheet.SheetError as se:
            set_label(self.mid_label,
                'Could not fetch the given Google sheet. Error: {}'.format(se.message))
            return
        finally:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

        listitems = [
            xbmcgui.ListItem(sheet_name)
            for sheet_name in self.sheet_names
        ]
        self.addItems(listitems)
        xbmc.sleep(100)
        self.setFocusId(self.getCurrentContainerId())


    def onAction(self, action):
        if action.getId() == xbmcgui.ACTION_SELECT_ITEM:
            selected_sheet = self.sheet_names[self.getCurrentListPosition()]
            show_main_window(self.sheet, selected_sheet)
        else:
            super(SelectSheetWindow, self).onAction(action)


def set_label(control, text):
    control.setLabel(text)


def show_notification(text):
    xbmc.log(text, level=xbmc.LOGWARNING)
    cmd = 'Notification(Remember Everything!, {}, 5000, {}/resources/icon.png)'.format(
        text, CWD)
    xbmc.executebuiltin(cmd)


def show_main_window(sheet_, selected_sheet):
    main_window = MainWindow(
        'main-window.xml', CWD, 'default', '1080i', False,
        sheet=sheet_, selected_sheet=selected_sheet)
    main_window.doModal()
    del main_window


def show_ui():
    client_id = kodiutils.get_setting('client_id')
    if not client_id:
        xbmcgui.Dialog().ok('Error', 'Google Client ID is missing. ',
            'Please update it in the settings and restart!')
        return

    client_secret = kodiutils.get_setting('client_secret')
    if not client_secret:
        xbmcgui.Dialog().ok('Error', 'Google Client secret is missing. ',
            'Please update it in the settings and restart!')
        return

    sheet_id = kodiutils.get_setting('sheet_id')
    if not sheet_id:
        xbmcgui.Dialog().ok('Error', 'Google Sheet ID is missing. ',
            'Please update it in the settings and restart!')
        return

    _sheet = sheet.GoogleSheets(client_id, client_secret, sheet_id)

    select_sheet_window = SelectSheetWindow(
        'select-sheet-window.xml', CWD, 'default', '1080i', True, sheet=_sheet)
    select_sheet_window.doModal()
    del select_sheet_window
