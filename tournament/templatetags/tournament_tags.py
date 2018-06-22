from django.utils.safestring import mark_safe
from django.template import Library

register = Library()


@register.simple_tag(takes_context=True)
def tourney_result(context):
    # note the use of takes_context = true.
    # this filter only works called from a context where player an opponent exists
    player = context['player']
    opponent = context['opponent']
    if 'tournament' in context:
        event = str(context['tournament'].pk) + '/'
    else:
        event = ''
    opponent_pk = opponent.pk
    html = ""
    if opponent_pk not in player.results:
        return ""
    result = player.results[opponent_pk]
    for game in result:
        points = str(game['p']).rpartition('+')[2]
        if points == 'Resign':
            points = 'R'
        # here, game['id'] would get you the id of the game to add a link
        html += '<a href="/tournament/' + event + 'games/' + str(game['id']) + '" \
                data-toggle="tooltip" title="' + player.user.username + ' vs ' +\
                opponent.user.username + ': ' + points + '">'
        if game['r'] == 1:
            html += '<i class="fa fa-check" aria-hidden="true" style="color:green"></i></a>'
        # will be glyphicon glyphicon-ok-circle or fontawesome thing
        else:
            html += '<i class="fa fa-remove"aria-hidden="true" style="color:red"></i></a>'

    return mark_safe(html)


@register.simple_tag(takes_context=True)
def match_result(context):
    match = context['match']
    tournament = context['tournament']
    if match.sgf is not None:
        sgf = match.sgf
        points = str(sgf.result).rpartition('+')[2]
        if points == 'Resign':
            points = 'R'
        html = '<a class="badge" href="/tournament/' + str(tournament.pk) + '/games/' + str(sgf.pk) + '">'
        html += '+' + points + '</a>'
    else:
        html = '<span class="badge" data-toggle="tooltip" title="'
        html += match.winner.user.username + ' won by forfeit">+F</span> '
    return mark_safe(html)



def rows(thelist, n):
    """
    Break a list into ``n`` rows, filling up each row to the maximum equal
    length possible. For example::

        >>> l = range(10)

        >>> rows(l, 2)
        [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

        >>> rows(l, 3)
        [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]

        >>> rows(l, 4)
        [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]

        >>> rows(l, 5)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]

        >>> rows(l, 9)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [], [], [], []]

        # This filter will always return `n` rows, even if some are empty:
        >>> rows(range(2), 3)
        [[0], [1], []]
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    list_len = len(thelist)
    split = list_len // n

    if list_len % n != 0:
        split += 1
    return [thelist[split*i:split*(i+1)] for i in range(n)]

def rows_distributed(thelist, n):
    """
    Break a list into ``n`` rows, distributing columns as evenly as possible
    across the rows. For example::

        >>> l = range(10)

        >>> rows_distributed(l, 2)
        [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

        >>> rows_distributed(l, 3)
        [[0, 1, 2, 3], [4, 5, 6], [7, 8, 9]]

        >>> rows_distributed(l, 4)
        [[0, 1, 2], [3, 4, 5], [6, 7], [8, 9]]

        >>> rows_distributed(l, 5)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]

        >>> rows_distributed(l, 9)
        [[0, 1], [2], [3], [4], [5], [6], [7], [8], [9]]

        # This filter will always return `n` rows, even if some are empty:
        >>> rows(range(2), 3)
        [[0], [1], []]
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    list_len = len(thelist)
    split = list_len // n

    remainder = list_len % n
    offset = 0
    local_rows = []
    for i in range(n):
        if remainder:
            start, end = (split+1)*i, (split+1)*(i+1)
        else:
            start, end = split*i+offset, split*(i+1)+offset
        local_rows.append(thelist[start:end])
        if remainder:
            remainder -= 1
            offset += 1
    return local_rows

def columns(thelist, n):
    """
    Break a list into ``n`` columns, filling up each column to the maximum equal
    length possible. For example::

        >>> from pprint import pprint
        >>> for i in range(7, 11):
        ...     print '%sx%s:' % (i, 3)
        ...     pprint(columns(range(i), 3), width=20)
        7x3:
        [[0, 3, 6],
         [1, 4],
         [2, 5]]
        8x3:
        [[0, 3, 6],
         [1, 4, 7],
         [2, 5]]
        9x3:
        [[0, 3, 6],
         [1, 4, 7],
         [2, 5, 8]]
        10x3:
        [[0, 4, 8],
         [1, 5, 9],
         [2, 6],
         [3, 7]]

        # Note that this filter does not guarantee that `n` columns will be
        # present:
        >>> pprint(columns(range(4), 3), width=10)
        [[0, 2],
         [1, 3]]
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    list_len = len(thelist)
    split = list_len // n
    if list_len % n != 0:
        split += 1
    return [thelist[i::split] for i in range(split)]

register.filter(rows)
register.filter(rows_distributed)
register.filter(columns)

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
