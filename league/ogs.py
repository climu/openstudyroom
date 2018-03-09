"""Get data from ogs api."""
from math import log, ceil

import requests


def get_user_rank(id_number):
    """Test if a id is registered in ogs and return his rank if so.
    Otherwise we return None"""
    if not id_number:
        return None
    url = 'https://online-go.com/api/v1/players/?id=' + str(id_number)
    request = requests.get(url).json()
    # Test if id exists at OGS.
    if request['count'] == 1:
        rtg = request['results'][0]['ratings']["overall"]["rating"]
        total = ceil(30 - (log(rtg / 850) / 0.032))
        if total <= 0:
            return str(abs(total - 1)) + "d"
        else:
            return str(total) + "k"
    else:
        return None


def get_user_id(username):
    """Test if a username is registered in ogs and return his id if so.
    Otherwise we return 0"""
    if not username:
        return 0
    url = 'https://online-go.com/api/v1/players/?username=' + username
    request = requests.get(url).json()
    # Test if usernmae exists at OGS.
    if request['count'] == 1:
        return request['results'][0]['id']
    else:
        return 0
