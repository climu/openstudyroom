import datetime

from league import utils


class TestUtils:
    def test_parse_sgf_string(self, sgf_text):
        parsed = utils.parse_sgf_string(sgf_text)
        expected = {
            'date': datetime.datetime(2016, 11, 19, 0, 0),
            'result': 'W+36.50',
            'bplayer': 'nomenest',
            'wplayer': 'climu',
            'komi': 0.50,
            'board_size': 19,
            'time': 60,
            'byo': '1x10 byo-yomi',
            'place': 'The KGS Go Server at http://www.gokgs.com/',
            'number_moves': 268,
            'check_code': '20161119climunomenestmnhnimcf11',
            'handicap': 1,
            'rules': 'Japanese',
        }
        assert parsed == expected

    def test_parse_ogs_iso8601_datetime(self):
        parsed = utils.parse_ogs_iso8601_datetime('2019-04-30T14:41:18.183258-04:00')
        expected = datetime.datetime(2019, 4, 30, 18, 41, 18, 183258)
        assert parsed == expected
