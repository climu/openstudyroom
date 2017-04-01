from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(takes_context=True)
def html_one_result(context):
	# note the use of takes_context = true.
	# this filter only works called from a context where player an opponent exists
	player=context['player']
	opponent = context['opponent']
	if not player.kgs_username in context['results']:
		return ""
	results = context['results'][player.kgs_username]['results']
	if 'event' in context:
		event=str(context['event'].pk)+'/'
	else:
		event=''

	opponent_kgs=opponent.kgs_username
	html=""
	if opponent_kgs in results:
		result=results[opponent_kgs]
		for game in result:
			#here, game['id'] would get you the id of the game to add a link
			html += '<a href="/league/'+ event + 'games/' + str(game['id']) + '">'
			if game['r']==1 :
				 html += '<i class="fa fa-circle-o" aria-hidden="true" style="color:green"></i></a>'
			#will be glyphicon glyphicon-ok-circle or fontawesome thing
			else :
			 html += '<i class="fa fa-circle" aria-hidden="true" style="color:blue"></i></a>'

	return mark_safe(html)

@register.simple_tag(takes_context=True)
def html_one_player_result(context):
	# note the use of takes_context = true.
	# this filter only works called from a context where player an opponent exists
	player=context['player']
	opponent = context['opponent']
	results = context['results']
	opponent_kgs=opponent.kgs_username
	html=""
	if opponent_kgs in results:
		result=results[opponent_kgs]
		for game in result:
			#here, game['id'] would get you the id of the game to add a link
			html += '<a href="/league/games/' + str(game['id']) + '">'
			if game['r']==1 :
				 html += '<i class="fa fa-circle-o" aria-hidden="true" style="color:green"></i></a>'
			#will be glyphicon glyphicon-ok-circle or fontawesome thing
			else :
			 html += '<i class="fa fa-circle" aria-hidden="true" style="color:blue"></i></a>'

	return mark_safe(html)

@register.filter
def user_link(user):
    link='<a href="/league/account/' + user.username + '">' + user.kgs_username +'</a>'
    return mark_safe(link)

@register.filter
def game_iframe_link(game):
	html= '<a href="/wgo/game/' + str(game.pk) + '"target="wgo_iframe">'+ str(game.sgf.result) + '</a>'
	return mark_safe(html)

@register.filter
def game_link(game,event=None):
	if event==None:
		html= '<a href="/league/games/' + str(game.pk) + '">'+ str(game.sgf.result) + '</a>'
	else:
		html= '<a href="/league/' + str(event.pk) + '/games/' + str(game.pk) + '">'+ str(game.sgf.result) + '</a>'

	return mark_safe(html)

@register.filter
def event_link(event):
	html= '<a href="/league/'+str(event.pk) +'">'+ str(event.name)+ '</a>'
	return mark_safe(html)

@register.filter
def division_link(division):
        html= '<a href="/league/'+str(division.league_event.pk) +'/results/'+ str(division.pk) +'">'+ str(division.name)+ '</a>'
        return mark_safe(html)

@register.filter(name='player_field')
def player_field(form, player_id):
        return form['player_'+str(player_id)]

@register.simple_tag(takes_context=True)
def player_field_tag(context):
	form=context['form']
	player = context['player']
	return form['player_'+str(player.pk)]

@register.filter
def boolean_icon(b):
	if b:
		 html = '<span class="glyphicon glyphicon-ok" aria-hidden="true"></span>'
	else:
		html = '<span class="glyphicon glyphicon-remove" aria-hidden="true"></span>'
	return mark_safe(html)

@register.filter()
def p_status(p_status):
	if p_status == 0:
		return mark_safe("0 : already scraped")
	elif p_status == 1:
		return mark_safe("1 : to be scraped")
	elif p_status == 2:
		return mark_safe("2 : to be scraped soon")
	else:
		return mark_safe(str(p_status) +" : something wrong")

@register.filter()
def scrap_time(n):
	return n*5

@register.filter()
def player_score(player, results):
	if player.kgs_username in results:
		return results[player.kgs_username]['score']
	else:
		return 0
