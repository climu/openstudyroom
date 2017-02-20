from django.shortcuts import render, get_object_or_404
from django.template import loader
from django.http import HttpResponse
from league.models import Sgf, Game
# Create your views here.
def wgo_game_view(request,game_id):
    # display a simple page with only wgo display
    # can easily be iframed.
    # Note: there might be a better way to dimamicly change a wgo content inside a page.
    #       I don't know how. wgo-data need sgf data which are inside the db.
    #       I guess an api:get_sgf_data could work but I have other things to do for now.
    game =get_object_or_404(Game,pk=game_id)
    sgf_data=game.sgf.sgf_text
    sgf_data=sgf_data.replace(chr(34), "")
    context={
    'sgf_data' : sgf_data,
    }
    return render(request,'wgo/wgo_iframe.html', context)
