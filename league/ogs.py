"""Get data from ogs api."""
import requests
from .models import Sgf


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
