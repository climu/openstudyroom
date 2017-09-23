"""Get data from ogs api."""
import requests
from .models import Sgf


def get_user_id(username):
    """Test if a username is registered in ogs and return his id if so.
    Otherwise we return 0"""
    url = 'https://online-go.com/api/v1/players/?username=' + username
    request = requests.get(url).json()
    # Test if usernmae exists at OGS.
    if request['count'] == 1:
        return request['results'][0]['id']
    else:
        return 0


def check_user_games(user):
    """ check if a user have played new games.
    still a draft"""
    ogs_id = user.profile.ogs_id
    url = 'https://online-go.com/api/v1/players/' + '40077' + '/games/?ordering=-ended'
    # we deal with pagination with this while loop
    while url != "null":
        request = requests.get(url).json()
        opponents_ogs_id = user.get_opponents()
        url = request['next']
        for game in request['results']:
            # first we check if we have the same  id in db.
            if Sgf.objects.filter(ogs_id=game['id']).exists():
                pass
            # we get opponent ogs id
            if game['white']['id'] == ogs_id:
                opponent_ogs_id = game['black']['id']
            else:
                opponent_ogs_id = game['white']['id']
            #if opponent_ogs_id not in

            pass
        sleep(2)
