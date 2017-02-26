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
	results=player.get_results()
	opponent_kgs=opponent.kgs_username
	html=""
	if opponent_kgs in results:
		result=results[opponent_kgs]
		for game in result:
			#here, game['id'] would get you the id of the game to add a link
			html += '<a href="/wgo/game/' + str(game['id']) + '"target="wgo_iframe">'
			if game['r']==1 :
				 html += '<i class="fa fa-circle-o" aria-hidden="true" style="color:green"></i></a>'
			#will be glyphicon glyphicon-ok-circle or fontawesome thing
			else :
			 html += '<i class="fa fa-circle" aria-hidden="true" style="color:blue"></i></a>'

	return mark_safe(html)

@register.filter
def nb_games(player):
	n = player.nb_win + player.nb_loss
	return n

@register.filter
def user_link(user):
    link='<a href="/league/account/' + user.username + '">' + user.kgs_username +'</a>'
    return mark_safe(link)

@register.filter
def game_link(game):
	html= '<a href="/wgo/game/' + str(game.pk) + '"target="wgo_iframe">'+ str(game.sgf.result) + '</a>'
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
