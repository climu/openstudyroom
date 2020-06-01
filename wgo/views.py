import os
import random
from openstudyroom.settings.base import BASE_DIR
from django.http import HttpResponse

def tsumego_api(request):
    """
    Returns one random tsumego from the folowing sets:
    - 0 cho elementary
    - 1 cho intermediate
    - 2 cho advanced
    - 3 gokyoshumyo
    - 4 hatsuyoron
    """
    set = random.choice(['cho-1-elementary', 'cho-2-intermediate', 'cho-3-advanced', 'gokyoshumyo', 'hatsuyoron'])
    sgf_file =  open(os.path.join(BASE_DIR,'wgo/tsumegos/' + set + '.sgf'), 'r')
    tsumego = random.choice(sgf_file.readlines())
    sgf_file.close()
    return HttpResponse(tsumego, content_type="text/plain")
