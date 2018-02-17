from django import template
from django.utils.safestring import mark_safe

from league.models import Registry

register = template.Library()


@register.simple_tag(takes_context=True)
def html_one_result(context):
    # note the use of takes_context = true.
    # this filter only works called from a context where player an opponent exists
    player = context['player']
    opponent = context['opponent']
    if 'event' in context:
        event = str(context['event'].pk) + '/'
    else:
        event = ''
    opponent_pk = opponent.pk
    html = ""
    if not opponent_pk in player.results:
        return ""
    result = player.results[opponent_pk]
    for game in result:
        # here, game['id'] would get you the id of the game to add a link
        html += '<a href="/league/' + event + 'games/' + str(game['id']) + '" \
                data-toggle="tooltip" title="' + player.user.username + ' vs ' + \
                opponent.user.username + '">'
        if game['r'] == 1:
            html += '<i class="fa fa-check" aria-hidden="true" style="color:green"></i></a>'
        # will be glyphicon glyphicon-ok-circle or fontawesome thing
        else:
            html += '<i class="fa fa-remove" aria-hidden="true" style="color:red"></i></a>'

    return mark_safe(html)


@register.simple_tag(takes_context=True)
def html_one_player_result(context):
    # note the use of takes_context = true.
    # this filter only works called from a context where player an opponent exists
    opponent = context['opponent']
    results = context['results']
    html = ""
    if opponent.user.pk in results:
        result = results[opponent.user.pk]
        for game in result:
            # here, game['id'] would get you the id of the game to add a link
            html += '<a href="/league/games/' + str(game['id']) + '">'
            if game['r'] == 1:
                html += '<i class="fa fa-check" aria-hidden="true" style="color:green"></i></a>'
            # will be glyphicon glyphicon-ok-circle or fontawesome thing
            else:
                html += '<i class="fa fa-remove" aria-hidden="true" style="color:red"></i></a>'

    return mark_safe(html)


@register.filter()
def user_link(user, meijin=None):
    if user is None:
        return ''
    link = '<a href="/league/account/' + user.username + '"'
    if user.is_online_kgs():
        link += 'class="online"'
    else:
        link += 'class="offline"'
    tooltip = ''
    if user.profile.kgs_username:
        k_info = user.profile.kgs_username + " " + user.profile.kgs_rank
        tooltip += '<p>KGS: ' + k_info + '</p>'
    if user.profile.ogs_username:
        o_info = user.profile.ogs_username + " " + user.profile.ogs_rank
        tooltip += '<p>OGS: ' + o_info + '</p>'

    link += 'data-toggle="tooltip" data-html="true" rel="tooltip" title="' + tooltip
    link += '" >' + user.username
    if user == meijin:
        link += ' <i class="fa fa-trophy"></i>'
    link += '</a>'
    return mark_safe(link)


@register.filter
def game_iframe_link(game):
    html = '<a href="/wgo/game/' + \
        str(game.pk) + '"target="wgo_iframe">' + str(game.sgf.result) + '</a>'
    return mark_safe(html)


@register.filter
def game_link(sgf, event=None):
    html = '<a role="button" onclick="load_game(' + \
        str(sgf.pk) + \
        ')">' + str(sgf.result) + '</a>'

    return mark_safe(html)


@register.filter
def event_link(event):
    html = '<a href="/league/' + str(event.pk) + '">'
    if event.community is not None:
        html += '(' + event.community.slug + ') '
    html += str(event.name) + '</a>'
    return mark_safe(html)


@register.filter
def division_link(division):
    html = '<a href="/league/' + str(division.league_event.pk) + \
        '/results/' + str(division.pk) + '">' + str(division.name) + '</a>'
    return mark_safe(html)


@register.filter(name='player_field')
def player_field(form, player_id):
    return form['player_' + str(player_id)]


@register.simple_tag(takes_context=True)
def player_field_tag(context):
    form = context['form']
    player = context['player']
    return form['player_' + str(player.pk)]


@register.filter
def boolean_icon(b):
    if b:
        html = '<span class="glyphicon glyphicon-ok" aria-hidden="true"></span>'
    else:
        html = '<span class="glyphicon glyphicon-remove" aria-hidden="true"></span>'
    return mark_safe(html)


@register.filter()
def p_status(status):
    if status == 0:
        return mark_safe("0 : already scraped")
    elif status == 1:
        return mark_safe("1 : to be scraped")
    elif status == 2:
        return mark_safe("2 : to be scraped soon")
    else:
        return mark_safe(str(status) + " : something wrong")


@register.filter()
def scrap_time(n):
    return n * 5


@register.filter()
def player_score(player, results):
    if player.kgs_username in results:
        return results[player.kgs_username]['score']
    else:
        return 0


@register.filter()
def player_nb_win(player, results):
    if player.kgs_username in results:
        return results[player.kgs_username]['nb_win']
    else:
        return 0


@register.filter()
def player_nb_loss(player, results):
    if player.kgs_username in results:
        return results[player.kgs_username]['nb_loss']
    else:
        return 0


@register.filter()
def player_nb_games(player, results):
    if player.kgs_username in results:
        return results[player.kgs_username]['nb_games']
    else:
        return 0


@register.simple_tag()
def get_meijin():
    r = Registry.objects.get(pk=1)
    return r.meijin
