# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import imaplib
import unittest

from mock import Mock, patch

from airflow import configuration, models
from airflow.contrib.hooks.imap_hook import ImapHook
from airflow.utils import db

imaplib_string = 'airflow.contrib.hooks.imap_hook.imaplib'


def _create_fake_imap(mock_imaplib, with_mail=False):
    mock_conn = Mock(spec=imaplib.IMAP4_SSL)
    mock_imaplib.IMAP4_SSL.return_value = mock_conn

    mock_conn.login.return_value = ('OK', [])

    if with_mail:
        mock_conn.select.return_value = ('OK', [])
        mock_conn.search.return_value = ('OK', [b'1'])
        mock_conn.fetch.return_value = ('OK', [(
            b'',  # ..because the email parser awaits 2 elements
            b'Content-Type: multipart/mixed; boundary=123\r\n--123\r\n'
            b'Content-Disposition: attachment; filename="test1.csv";'
            b'Content-Transfer-Encoding: base64\r\nSWQsTmFtZQoxLEZlbGl4\r\n--123--'
        )])
        mock_conn.close.return_value = ('OK', [])

    mock_conn.logout.return_value = ('OK', [])

    return mock_conn


class TestImapHook(unittest.TestCase):
    def setUp(self):
        configuration.load_test_config()

        db.merge_conn(
            models.Connection(
                conn_id='imap_default',
                host='imap_server_address',
                login='imap_user',
                password='imap_password'
            )
        )

    @patch(imaplib_string)
    def test_connect_and_disconnect(self, mock_imaplib):
        mock_conn = _create_fake_imap(mock_imaplib)

        with ImapHook():
            pass

        mock_imaplib.IMAP4_SSL.assert_called_once_with('imap_server_address')
        mock_conn.login.assert_called_once_with('imap_user', 'imap_password')
        mock_conn.logout.assert_called_once()

    @patch(imaplib_string)
    def test_has_mail_attachments_found(self, mock_imaplib):
        _create_fake_imap(mock_imaplib, with_mail=True)

        with ImapHook() as imap_hook:
            has_attachment_in_inbox = imap_hook.has_mail_attachments('test1.csv')

        self.assertTrue(has_attachment_in_inbox)

    @patch(imaplib_string)
    def test_has_mail_attachments_not_found(self, mock_imaplib):
        _create_fake_imap(mock_imaplib, with_mail=True)

        with ImapHook() as imap_hook:
            has_attachment_in_inbox = imap_hook.has_mail_attachments('test1.txt')

        self.assertFalse(has_attachment_in_inbox)

    @patch(imaplib_string)
    def test_has_mail_attachments_with_regex_found(self, mock_imaplib):
        _create_fake_imap(mock_imaplib, with_mail=True)

        with ImapHook() as imap_hook:
            has_attachment_in_inbox = imap_hook.has_mail_attachments(
                name='test(\d+).csv',
                check_regex=True
            )

        self.assertTrue(has_attachment_in_inbox)

    @patch(imaplib_string)
    def test_has_mail_attachments_with_regex_not_found(self, mock_imaplib):
        _create_fake_imap(mock_imaplib, with_mail=True)

        with ImapHook() as imap_hook:
            has_attachment_in_inbox = imap_hook.has_mail_attachments(
                name='test_(\d+).csv',
                check_regex=True
            )

        self.assertFalse(has_attachment_in_inbox)

    @patch(imaplib_string)
    def test_retrieve_mail_attachments_found(self, mock_imaplib):
        _create_fake_imap(mock_imaplib, with_mail=True)

        with ImapHook() as imap_hook:
            attachments_in_inbox = imap_hook.retrieve_mail_attachments('test1.csv')

        self.assertEquals(attachments_in_inbox, [('test1.csv', b'SWQsTmFtZQoxLEZlbGl4')])

    @patch(imaplib_string)
    def test_retrieve_mail_attachments_not_found(self, mock_imaplib):
        _create_fake_imap(mock_imaplib, with_mail=True)

        with ImapHook() as imap_hook:
            attachments_in_inbox = imap_hook.retrieve_mail_attachments('test1.txt')

        self.assertEquals(attachments_in_inbox, [])

    @patch(imaplib_string)
    def test_retrieve_mail_attachments_with_regex_found(self, mock_imaplib):
        _create_fake_imap(mock_imaplib, with_mail=True)

        with ImapHook() as imap_hook:
            attachments_in_inbox = imap_hook.retrieve_mail_attachments(
                name='test(\d+).csv',
                check_regex=True
            )

        self.assertEquals(attachments_in_inbox, [('test1.csv', b'SWQsTmFtZQoxLEZlbGl4')])

    @patch(imaplib_string)
    def test_retrieve_mail_attachments_with_regex_not_found(self, mock_imaplib):
        _create_fake_imap(mock_imaplib, with_mail=True)

        with ImapHook() as imap_hook:
            attachments_in_inbox = imap_hook.retrieve_mail_attachments(
                name='test_(\d+).csv',
                check_regex=True
            )

        self.assertEquals(attachments_in_inbox, [])

    # TODO Add test_download_mail_attachments_found
    # TODO Add test_download_mail_attachments_not_found
    # TODO Add test_download_mail_attachments_with_regex_found
    # TODO Add test_download_mail_attachments_with_regex_not_found


if __name__ == '__main__':
    unittest.main()
