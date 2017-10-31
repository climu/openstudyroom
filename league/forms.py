from django import forms
from django.contrib.auth.models import  Group
from django.forms import ModelForm
import pytz

from .models import Division, LeagueEvent, Profile
from .ogs import get_user_id

class SgfAdminForm(forms.Form):
    sgf = forms.CharField(label='sgf data', widget=forms.Textarea(attrs={'cols': 60, 'rows': 20}))
    url = forms.CharField(label="KGS archive link", required=False)

class ActionForm(forms.Form):
    action = forms.CharField(label='action', widget=forms.HiddenInput())
    user_id = forms.IntegerField(label='user_id', widget=forms.HiddenInput(), required=False)
    next = forms.CharField(label='next', widget=forms.HiddenInput(), required=False)


class LeagueSignupForm(forms.Form):
    kgs_username = forms.CharField(max_length=10, required=False)
    ogs_username = forms.CharField(max_length=40, required=False)
    timezone = forms.ChoiceField(
        label='Time Zone',
        choices=[(t, t) for t in pytz.common_timezones],
        required=False,
        initial='UTC'
    )

    def clean_kgs_username(self):
        if not self.cleaned_data['kgs_username']:
            return ''
        kgs_username = self.cleaned_data['kgs_username']
        if Profile.objects.filter(kgs_username__iexact=kgs_username).exists():
            self.add_error('kgs_username', "This kgs username is already used by one of our member. You should contact us")
        return kgs_username

    def clean_ogs_username(self):
        # Check ogs username to be registered and update ogs_id
        if not self.cleaned_data['ogs_username']:
            return ''
        ogs_username = self.cleaned_data['ogs_username']
        if Profile.objects.filter(ogs_username__iexact=ogs_username).exists():
            self.add_error('ogs_username', 'Someone is already using this OGS username. Please contact an admin')
        id = get_user_id(ogs_username)
        if id == 0:
            self.add_error('ogs_username', 'There is no such user registered at the Online Go Server')
        return ogs_username

    def clean(self):
        super(LeagueSignupForm, self).clean()
        if not (self.cleaned_data['kgs_username'] or self.cleaned_data['ogs_username']):
            self.add_error('kgs_username', '')
            self.add_error('ogs_username', '')
            raise forms.ValidationError("You should enter OGS or KGS username")
        return self.cleaned_data

    def signup(self, request, user):
        user.kgs_username = self.cleaned_data['kgs_username']
        group = Group.objects.get(name='new_user')
        user.groups.add(group)
        user.save()
        id = get_user_id(self.cleaned_data['ogs_username'])
        profile = Profile(
            user=user,
            kgs_username=user.kgs_username,
            ogs_username=self.cleaned_data['ogs_username'],
            ogs_id=id,
            timezone=self.cleaned_data['timezone']
        )
        profile.save()


class UploadFileForm(forms.Form):
    file = forms.FileField()

class LeaguePopulateForm(forms.Form):
    # a form related to a set of leagueplayers with one field per player.
    def __init__(self, from_event, to_event, *args, **kwargs):
        super(LeaguePopulateForm, self).__init__(*args, **kwargs)
        players = from_event.get_players()
        divisions = to_event.get_divisions()
        for player in players:
            choices = [(division.pk, division.name) for division in divisions] + [(0, 'drop')]
            self.fields['player_'+str(player.pk)] = forms.ChoiceField(choices=choices, required=False)
            # an attempt to set initial choice with same order... failed.
            #division =divisions.filter(order=player.division.order).first()
            #if division != None:
            #    self.fields['player_'+str(player.pk)].inital = (division.pk,division.name)

class DivisionForm(ModelForm):
    class Meta:
        model = Division
        fields = ['name']


class LeagueEventForm(forms.ModelForm):
    class Meta:
        model = LeagueEvent
        fields = [
            'name',
            'event_type',
            'begin_time',
            'end_time',
            'nb_matchs',
            'ppwin',
            'pploss',
            'min_matchs',
            'tag',
            'server',
            'main_time',
            'byo_time',
            'is_open',
            'is_public',
            'description',
        ]
        widgets = {
            'name': forms.TextInput(),
            'begin_time': forms.SelectDateWidget(),
            'end_time': forms.SelectDateWidget(),
        }

class EmailForm(forms.Form):
    subject = forms.CharField(required=True)
    copy_to = forms.CharField(required=False)
    message = forms.CharField(widget=forms.Textarea())

class TimezoneForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['timezone']


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = [
            'bio',
            'ogs_username',
            'kgs_username',
        ]

    def clean_kgs_username(self):
        if not self.cleaned_data['kgs_username']:
            return ''
        kgs_username = self.cleaned_data['kgs_username']
        if Profile.objects.filter(kgs_username__iexact=kgs_username).\
                exclude(pk=self.instance.pk).exists():
            self.add_error('kgs_username', 'Someone is already using this KGS username. Please contact an admin')
        else:  # Update all related league players kgs username
            open_players = self.instance.user.leagueplayer_set.filter(event__is_open=True)
            open_players.update(kgs_username=kgs_username)
        return kgs_username

    def clean_ogs_username(self):
        if not self.cleaned_data['ogs_username']:
            return ''
        # Check ogs username to be registered and update ogs_id
        ogs_username = self.cleaned_data['ogs_username']
        if ogs_username:
            id = get_user_id(ogs_username)
            if id == 0:
                self.add_error('ogs_username', 'There is no such user registered at the Online Go Server')
            elif Profile.objects.filter(ogs_username__iexact=ogs_username).\
                    exclude(pk=self.instance.pk).exists():
                self.add_error('ogs_username', 'Someone is already using this OGS username. Please contact an admin')
            else:
                # update ogs_id
                self.instance.ogs_id = id
                self.instance.save()
                # update all related players ogs usernames
                open_players = self.instance.user.leagueplayer_set.filter(event__is_open=True)
                open_players.update(ogs_username=ogs_username)
        return ogs_username

    def clean(self):
        super(ProfileForm, self).clean()
        if not (self.cleaned_data['kgs_username'] or self.cleaned_data['ogs_username']):
            self.add_error('kgs_username', '')
            self.add_error('ogs_username', '')
            raise forms.ValidationError("You should enter OGS or KGS username")
        return self.cleaned_data
