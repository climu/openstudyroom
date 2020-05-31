# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestGamesDatatableAPI.test_with_sgf 1'] = {
    'data': [
        [
            '2020-05-29',
            {
                'account_url': '/league/account/cho_chikun',
                'discord_data': None,
                'discord_online': False,
                'is_meijin': False,
                'is_online': False,
                'kgs_data': None,
                'kgs_online': False,
                'ogs_data': None,
                'ogs_online': False,
                'username': 'cho_chikun',
                'winner': True
            },
            {
                'account_url': '/league/account/kobayashi_koichi',
                'discord_data': None,
                'discord_online': False,
                'is_meijin': False,
                'is_online': False,
                'kgs_data': None,
                'kgs_online': False,
                'ogs_data': None,
                'ogs_online': False,
                'username': 'kobayashi_koichi',
                'winner': False
            },
            {
                'sgf_pk': 1,
                'sgf_result': '?'
            }
        ]
    ],
    'draw': 0,
    'recordsTotal': 1
}

snapshots['TestGamesDatatableAPI.test_with_league 1'] = {
    'data': [
        [
            '2020-05-29',
            {
                'account_url': '/league/account/cho_chikun',
                'discord_data': None,
                'discord_online': False,
                'is_meijin': False,
                'is_online': False,
                'kgs_data': None,
                'kgs_online': False,
                'ogs_data': None,
                'ogs_online': False,
                'username': 'cho_chikun',
                'winner': True
            },
            {
                'account_url': '/league/account/kobayashi_koichi',
                'discord_data': None,
                'discord_online': False,
                'is_meijin': False,
                'is_online': False,
                'kgs_data': None,
                'kgs_online': False,
                'ogs_data': None,
                'ogs_online': False,
                'username': 'kobayashi_koichi',
                'winner': False
            },
            {
                'sgf_pk': 1,
                'sgf_result': '?'
            }
        ]
    ],
    'draw': 0,
    'recordsTotal': 1
}
