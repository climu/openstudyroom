import datetime

from django import forms
from django.contrib.auth.models import Group
from django.forms import ModelForm
from django_countries.widgets import CountrySelectWidget
import pytz

from .models import Division, LeagueEvent, Profile
from .ogs import get_user_id, get_user_rank


class SgfAdminForm(forms.Form):
    sgf = forms.CharField(label='sgf data', widget=forms.Textarea(attrs={'cols': 60, 'rows': 20}))
    url = forms.CharField(label="KGS archive link", required=False)

class ActionForm(forms.Form):
    action = forms.CharField(label='action', widget=forms.HiddenInput(), required=False)
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
        profile = Profile(
            user=user,
            timezone=self.cleaned_data['timezone']
        )
        if self.cleaned_data['kgs_username']:
            profile.kgs_username = self.cleaned_data['kgs_username']
        if self.cleaned_data['ogs_username']:
            profile.ogs_username = self.cleaned_data['ogs_username']
            id = get_user_id(self.cleaned_data['ogs_username'])
            profile.ogs_id = id
            id = get_user_id(self.cleaned_data['ogs_username'])
            if id > 0:
                profile.ogs_rank = get_user_rank(id)
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
    next = forms.CharField(label='next', widget=forms.HiddenInput(), required=False)
    class Meta:
        model = Division
        fields = ['name', 'next']


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
            'board_size',
            'komi',
            'clock_type',
            'main_time',
            'additional_time',
            'is_open',
            'is_public',
            'description',
            'prizes'
        ]
        # Customise year list to show 2 years in the past/future
        EVENT_YEAR_CHOICES = range(datetime.date.today().year - 2, datetime.date.today().year + 3)
        widgets = {
            'name': forms.TextInput(),
            'begin_time': forms.SelectDateWidget(years=EVENT_YEAR_CHOICES),
            'end_time': forms.SelectDateWidget(years=EVENT_YEAR_CHOICES),
        }
        help_texts = {
            'name': "Name of the league",
            'event_type': 'League will work',
            'begin_time': "UTC time at 00:00.",
            'end_time': "Set it to the 1st to have full month.",
            'nb_matchs': 'Maximum number of match two players can play together',
            'ppwin': 'Point per win',
            'pploss': 'Point per loss',
            'min_matchs': 'Minimum of match for a user to be considered active',
            'is_open': 'Can people register and game get scraped?',
            'is_public': 'Can people see the league?',
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
            'country',
            'go_quest_username'
        ]
        widgets = {'country': CountrySelectWidget()}

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

    def clean_go_quest_username(self):
        if not self.cleaned_data['go_quest_username']:
            return ''
        go_quest_username = self.cleaned_data['go_quest_username']
        if go_quest_username:
            if Profile.objects.filter(go_quest_username__iexact=go_quest_username).\
                    exclude(pk=self.instance.pk).exists():
                self.add_error(
                    'go_quest_username',
                    'Someone is already using this Go Quest username. Please contact an admin'
                )
            else:
                # udate goquest username for all players
                open_players = self.instance.user.leagueplayer_set.filter(event__is_open=True)
                open_players.update(go_quest_username=go_quest_username)
                print(open_players)
        return go_quest_username

    def clean(self):
        super(ProfileForm, self).clean()
        if not (self.cleaned_data['kgs_username'] or self.cleaned_data['ogs_username']):
            self.add_error('kgs_username', '')
            self.add_error('ogs_username', '')
            raise forms.ValidationError("You should enter OGS or KGS username")
        return self.cleaned_data
