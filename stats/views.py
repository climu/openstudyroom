import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Case, Count, IntegerField, When
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.template import loader

from league.models import LeagueEvent, Sgf, User


def overview(request):
    """Render various stats OSR related"""
    osr_leagues = LeagueEvent.objects.filter(
                    is_public=True,
                    community__isnull=True
                )
    games = Sgf.objects\
        .exclude(date__isnull=True)\
        .defer('sgf_text')\
        .filter(league_valid=True)\
        .filter(events__in=osr_leagues)\
        .distinct()\
        .annotate(month=TruncMonth('date'))\
        .values('month')\
        .annotate(total=Count('id'))\
        .annotate(kgs=Count(
            Case(
                When(place__startswith='The KGS', then=1),
                output_field=IntegerField(),
                distinct=True
            )))\
        .annotate(ogs=Count(
            Case(
                When(place__startswith='OGS', then=1),
                output_field=IntegerField(),
                distinct=True
            )))\
        .values('month', 'total', 'kgs', 'ogs')\
        .order_by('month')
    games = list(games)
    games = json.dumps(games, cls=DjangoJSONEncoder)

    registrations = User.objects\
        .annotate(month=TruncMonth('date_joined'))\
        .values('month')\
        .annotate(total=Count('id'))\
        .values('month', 'total')\
        .order_by('month')

    registrations = list(registrations)
    users = []
    total = 0
    for month in registrations:
        total += month['total']
        dict = {
            'total': total,
            'month': month['month']
        }
        users.append(dict)

    users = json.dumps(users, cls=DjangoJSONEncoder)
    registrations = json.dumps(registrations, cls=DjangoJSONEncoder)
    context = {
        'games': games,
        'registrations': registrations,
        'users': users
    }

    template = loader.get_template('stats/overview.html')
    return HttpResponse(template.render(context, request))
