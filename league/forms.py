from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import  Group
class SgfAdminForm(forms.Form):
    sgf = forms.CharField(label='sgf data',widget=forms.Textarea(attrs={'cols': 60, 'rows': 20}))

class ActionForm(forms.Form):
    action = forms.CharField(label ='action',widget=forms.HiddenInput())
    user_id= forms.IntegerField(label ='user_id',widget=forms.HiddenInput(),required=False)

class LeagueSignupForm(forms.Form):
    kgs_username = forms.CharField(max_length=10,required=True,)

    def signup(self, request, user):
        user.kgs_username = self.cleaned_data['kgs_username']
        group = Group.objects.get(name='new_user')
        user.groups.add(group)
        user.save()


class UploadFileForm(forms.Form):
    file = forms.FileField()

class LeagueRolloverForm(forms.Form):
    # a form related to a set of leagueplayers with one field per player.
    def __init__(self, from_event,to_event,  *args, **kwargs):
        super(LeagueRolloverForm, self).__init__(*args, **kwargs)
        players = from_event.get_players()
        divisions = to_event.get_divisions()
        for player in players:
            self.fields[ 'player_'+str(player.pk)] = forms.ChoiceField(choices=[(division.pk,division.name) for division in divisions])
            # an attempt to set initial choice with same order... failed.
            #division =divisions.filter(order=player.division.order).first()
            #if division != None:
            #    self.fields['player_'+str(player.pk)].inital = (division.pk,division.name)
