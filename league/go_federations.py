""" Get data from go Federations"""
from math import ceil
import requests

def get_egf_rank(egf_id):
    """
    Check if an EGF id is valid and get its rank.
    We return the rank (a string) or None if it's not valid
    https://senseis.xmp.net/?EGFRatingSystem
    """
    url = "https://www.europeangodatabase.eu/EGD/GetPlayerDataByPIN.php?pin=" + str(egf_id)
    request = requests.get(url, timeout=10).json()
    if request['retcode'] == "Ok":
        gor = int(round(int(request['Gor']), -2)/100)
        if gor > 20:
            return f'{gor - 20}d'
        else:
            return f'{21 - gor}k'
    return None

def ffg_rating2rank(rating):
    """
    Convert a FFG rating into a Go rank
    """
    if rating in ("NC", "-9999"):
        return "NC"
    else:
        return str(ceil(abs(int(rating)/100))) + ('D' if int(rating) > 0 else 'K')

def get_ffg_rank(ffg_licence_number):
    """
    Check if a FFG licence number is valid and get its rank.
    We return the rank (a string) or None if it's not valid
    """
    # url = "https://ffg.jeudego.org/echelle/echtxt/echelle.txt"
    url = "https://ffg.jeudego.org/echelle/echtxt/ech_ffg_V3.txt"
    request = requests.get(url, timeout=10)
    if request.status_code == 200:
        infos = ffg_user_infos_alternative(ffg_licence_number, request.text)
        if infos is not None:
            return ffg_rating2rank(infos['rating'])
    return None

def ffg_user_infos(ffg_licence_number, echelle_ffg):
    """
    Check if a FFG licence number is in ffg_infos and parse related informations.
    echelle_ffg is a string from https://ffg.jeudego.org/echelle/echtxt/echelle.txt.
    If the licence number is in ffg_infos return a dict formated as:
    {'name': string, 'rating': string, 'club': string}
    Return None if the licence number is not in ffg_infos.

    Exemple of ffg_infos lines:
    1400315 HWANG In-seong            720        38Gr
    1800104 PORTEJOIE-KALINCHENKO Gu-2950        44Na
    2100088 ABIASSI Samuel             NC        38Gr
    0123456789012345678901234567890123456789012345678
    """
    # get first line starting with licence number.
    # we skip 3 first lines that are headers
    line = None
    for l in echelle_ffg.splitlines()[3:]:
        if l.split(' ')[0] == ffg_licence_number:
            line = l
            break
    if line is None:
        return None
    else:
        return {
            'name': line[8:32].rstrip(),
            'rating': line[32:37].lstrip(),
            'club': line[45:49].lstrip()
        }

def ffg_user_infos_alternative(ffg_licence_number, echelle_ffg):
    """because
    https://ffg.jeudego.org/echelle/echtxt/ech_ffg_V3.txt
    seems to be more frequently updated,
    We might just remove
    https://ffg.jeudego.org/echelle/echtxt/echelle.txt
    in the future.

    echelle_ffg is formated as such :
    AAIJ René                               243 e ------- xxxx NL
    AAKERBLOM Charlie                       433 e ------- xxxx SE
    ABAD Jahin                            -3000 - 2000205 38GJ FR
    ABADIA Mickaël                        -1400 - 9728205 94MJ FR
    ABADIE Yves                           -1500 - 0452000 31To FR
    """
    # we skip first line that is header
    line = None
    for l in echelle_ffg.splitlines()[1:]:
        if l[46:53] == ffg_licence_number:
            line = l
            break
    if line is None:
        return None
    else:
        return {
            'name': line[:38].rstrip(),
            'rating': line[38:43].lstrip(),
            'club': line[54:58]
        }


def format_ffg_tou(league, licences, location=None, comment=None):
    """
    format a division results in tou format for the French Go fédération.
    https://ffg.jeudego.org/echelle/format_res.php
    ;name=Exemple
    ;date=08/01/2005
    ;comm=4eme tour du championnat d'Auvergne maritime
    ;
    ;Num Nom Prénom               Niv Licence Club
       1 LIM Eugène                4D 7900001 75Pa    2+w0    4+w2    3-b0
       2 LI Zheng                  4D 0116000 00L8    1-b0    5-w4    4-w1
       3 MARTIN Luc                1D 9785526 68RJ    0=      0=      1+w0
       4 LE_BERRE Bruno            1K 9034000 76Ro    5+w0    1-b2    2+b1
       5 KIM Ii-Hyun               3K 9343002 76Ro    4-b0    2+b4    7-w8
       6 DE_TREGLODE Dominique     8K 9525023 29Ba    7+w2    9-w7    8-w6
       7 DECHAUME-MONTCHARMONT Fr 12K 0125006 75Pa    6-b2    8-w2    5+b8
       8 ABADIA Mickaël           16K 9728205 94MJ    9-w0    7+b2    6+b6
       9 VAN_DE_PUTTE Bart        17K ------- BE      8+b0    6+b7    0=
    ;size=19
    ;time=45
    ;komi=7.5
    """
    # Create the header
    tou = f';name={league.name}\n'
    date = league.begin_time.strftime("%d/%m/%Y")
    tou += f';date={date}\n'
    if location:
        tou += f';vill={location}\n'
    if comment:
        tou += f';comm={comment}\n'
    tou += f';size={league.board_size}\n'
    # clock_type is 'byoyomi' or 'fisher'
    tou += f';time={league.main_time/60:.0f}+{league.clock_type[0]}\n'
    tou += f';komi={league.komi}\n'
    tou += f';vill={league.servers}\n'
    tou += ';prog=https://github.com/climu/openstudyroom/\n'
    tou += ';\n'
    tou += ';Num Nom Prénom               Niv Licence Club\n'

    # get the last FFG information
    url = "https://ffg.jeudego.org/echelle/echtxt/ech_ffg_V3.txt"
    request = requests.get(url, timeout=10)
    if request.status_code != 200:
        return None
    echelle_ffg = request.text

    sgfs = league.sgf_set.exclude(winner__isnull=True).\
        defer('sgf_text').select_related('winner', 'white', 'black').all()
    players = league.leagueplayer_set.all().prefetch_related('user__profile')

    # First add extra fields to players
    for idx, player in enumerate(players):
        # if a player does not have a licence number we return None
        licence_number = licences[player.user.username]
        if licence_number is None or licence_number == 0:
            return None
        infos = ffg_user_infos_alternative(licence_number, echelle_ffg)
        if infos is None:
            return None
        player.num = idx + 1
        player.name = infos["name"]
        player.rank = ffg_rating2rank(infos['rating'])
        player.licence_number = licence_number
        player.club = infos["club"]
        player.results = '' #    2+w0    4+w2    3-b0

    # we create a list of round.
    # We will put the sgfs inside each round so a player can only play one game per round.
    # rounds = [{"users": [list of users who played this round], "sgfs": [list of sgfs]}]
    rounds = [{'users':[], 'sgfs':[]}]
    for sgf in sgfs:
        # we put the sgf in the first round where both player have not played yet
        in_round = False
        for round in rounds:
            if sgf.black not in round['users'] and sgf.white not in round['users']:
                round['sgfs'].append(sgf)
                round['users'].extend([sgf.white, sgf.black])
                in_round = True
                break
        # if no round can welcome this sgf, we create a new round
        if not in_round:
            rounds.append({
                'users': [sgf.white, sgf.black],
                'sgfs': [sgf]
            })

    # render players results per round
    for round in rounds:
        for sgf in round['sgfs']:
            if sgf.winner == sgf.white:
                loser = next(player for player in players if player.user == sgf.black)
                winner = next(player for player in players if player.user == sgf.white)
                loser.results += f'{winner.num:>5}-b{sgf.handicap}'
                winner.results += f'{loser.num:>5}+w{sgf.handicap}'
            else:
                loser = next(player for player in players if player.user == sgf.white)
                winner = next(player for player in players if player.user == sgf.black)
                loser.results += f'{winner.num:>5}-w{sgf.handicap}'
                winner.results += f'{loser.num:>5}+b{sgf.handicap}'
        # add 0= for players who didn't participate in the round
        for player in players:
            if player.user not in round['users']:
                player.results += '    0=  '

    for player in players:
        tou += f'{player.num:>4} {player.name:24} {player.rank:>3} {player.licence_number}'
        tou += f' {player.club:4}{player.results}\n'
    # add the footer

    return tou
