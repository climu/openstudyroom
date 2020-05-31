import os
import random
from openstudyroom.settings.base import BASE_DIR
from django.http import HttpResponse

def tsumego_api(request):
    """
    Returns one random tsumego from the folowings set:
    - cho elementary
    - cho intermediate
    - cho advanced
    - gokyoshumyo
    - hatsuyoron
    """

    sgf_file =  open(os.path.join(BASE_DIR,'wgo/tsumegos/cho-1-elementary.sgf'), 'r')
    tsumego = random.choice(sgf_file.readlines())
    sgf_file.close()
    return HttpResponse(tsumego, content_type="text/plain")
