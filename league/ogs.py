"""Get data from ogs api."""
from math import log, ceil
import requests

def rating2rank(ogs_rating):
    """Return a human readable go rank from a OGS rating number"""
    total = ceil(30 - (log(ogs_rating / 525) * 23.15)) # https://forums.online-go.com/t/2021-rating-and-rank-adjustments/33389
    if total <= 0:
        return str(abs(total - 1)) + "d"
    else:
        return str(total) + "k"

def get_user_rank(id_number):
    """Test if a id is registered in ogs and return his rank if so.
    Otherwise we return None"""
    if not id_number:
        return None
    url = 'https://online-go.com/api/v1/players/?id=' + str(id_number)
    request = requests.get(url, timeout=10).json()
    # Test if id exists at OGS.
    if request['count'] == 1:
        rating = request['results'][0]['ratings']["overall"]["rating"]
        return rating2rank(rating)
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

def get_online_users():
    url = 'https://online-go.com/termination-api/chat/group-1843/users'
    request = requests.get(url, timeout=10).json()
    return request
