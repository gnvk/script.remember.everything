from datetime import datetime
import json
import os
import requests
import time
import xbmcgui

from . import DATA_DIR
from .card import Card

class SheetError(Exception):
    pass


class GoogleSheets(object):

    _BASE_URL = 'https://sheets.googleapis.com/v4/spreadsheets'

    def __init__(self, client_id, client_secret, sheet_id):
        self._client_id = client_id
        self._client_secret = client_secret
        self._sheet_id = sheet_id
        self._cred_path = os.path.join(DATA_DIR, 'creds.json')
        self._load_tokens()

    def get_cards(self):
        url = '{}/{}/values/A2:I'.format(self._BASE_URL, self._sheet_id)
        resp = requests.get(url, headers={
            'Authorization': 'Bearer ' + self._token
        })
        self._check_resp(resp)
        rows = resp.json()['values']
        for i, row in enumerate(rows):
            if len(row) < 7:
                continue
            card = Card(
                idx=2 + i, question=row[5], answer=row[6],
                first_practice=row[0], next_practice=row[1],
                streak=row[2], interval=row[3], easiness=row[4]
            )
            if len(row) > 7:
                card.question_picture = row[7]
            if len(row) > 8:
                card.answer_picture = row[8]
            yield card

    def update_card(self, card):
        # type: (card) -> None
        url = '{0}/{1}/values/A{2}:E{2}?valueInputOption=RAW'.format(
            self._BASE_URL, self._sheet_id, card.idx)
        resp = requests.put(url, json={
            'values': [
                [
                    card.first_practice,
                    card.next_practice,
                    card.streak,
                    card.interval,
                    card.easiness
                ]
            ]
        }, headers={
            'Authorization': 'Bearer ' + self._token
        })
        self._check_resp(resp)

    @property
    def _token(self):
        if self._access_token_expires_at <= int(time.time()):
            self._refresh_access_token()
        return self._access_token

    def _check_resp(self, resp):
        if not resp.ok:
            raise SheetError(resp.text)

    def _save_tokens(self):
        tokens = {
            'access_token': self._access_token,
            'expires_at': self._access_token_expires_at,
            'refresh_token': self._refresh_token
        }
        with open(self._cred_path, mode='w') as cred_file:
            json.dump(tokens, cred_file)

    def _load_tokens(self):
        if not os.path.exists(self._cred_path):
            self._login()
            return
        with open(self._cred_path) as cred_file:
            content = json.load(cred_file)
        self._access_token = content['access_token']
        self._access_token_expires_at = content['expires_at']
        self._refresh_token = content['refresh_token']

    def _login(self):
        resp = requests.post('https://oauth2.googleapis.com/device/code', data={
            'client_id': self._client_id,
            'scope': 'https://www.googleapis.com/auth/spreadsheets'
        })
        self._check_resp(resp)
        content = resp.json()

        device_code = content['device_code']
        user_code = content['user_code']
        verification_url = content['verification_url']

        message = 'Please visit {} and type code {}'.format(
            verification_url, user_code)
        # TODO: Replace with progress dialog and poll
        xbmcgui.Dialog().ok('Login', message)

        resp = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'device_code': device_code,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
        }, headers={
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        self._check_resp(resp)
        content = resp.json()
        self._access_token = content['access_token']
        self._access_token_expires_at = int(
            time.time()) + content['expires_in']
        self._refresh_token = content['refresh_token']
        self._save_tokens()

    def _refresh_access_token(self):
        resp = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'refresh_token': self._refresh_token,
            'grant_type': 'refresh_token'
        }, headers={
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        self._check_resp(resp)
        content = resp.json()
        self._access_token = content['access_token']
        self._access_token_expires_at = int(
            time.time()) + content['expires_in']
        self._save_tokens()
