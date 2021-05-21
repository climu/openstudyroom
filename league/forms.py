import datetime

from django import forms
from django.contrib.auth.models import Group
from django.forms import ModelForm
from django.utils.timezone import make_aware
from django.core.exceptions import ValidationError
from django_countries.widgets import CountrySelectWidget
import pytz
from community.models import Community
from community.widget import Community_select
from .models import Division, LeagueEvent, Profile
from .ogs import get_user_id, get_user_rank
from .go_federations import get_egf_rank, get_ffg_rank

class MultipleValueWidget(forms.TextInput):
    def value_from_datadict(self, data, files, name):
        return data.getlist(name)

class MultipleIntField(forms.Field):
    widget = MultipleValueWidget
    def __init__(self, length=None):
        super().__init__()
        self.length = length
    def clean_int(self, x):
        try:
            return int(x)
        except:
            raise ValidationError("Cannot convert to integer: {}".format(repr(x)))
    def clean(self, value):
        if self.length is len(value) or self.length is None:
            return [self.clean_int(x) for x in value]
        else:
            raise ValidationError("List integer must be of length: {}".format(repr(self.length)))

class SgfAdminForm(forms.Form):
    sgf = forms.CharField(label='sgf data', widget=forms.Textarea(attrs={'cols': 60, 'rows': 20}))
    url = forms.CharField(label="KGS archive link", required=False)

class AddWontPlayForm(forms.Form):
    players = MultipleIntField(2)

class RemoveWontPlayForm(forms.Form):
    sgfs = MultipleIntField()

class ActionForm(forms.Form):
    action = forms.CharField(label='action', widget=forms.HiddenInput(), required=False)
    user_id = forms.IntegerField(label='user_id', widget=forms.HiddenInput(), required=False)
    next = forms.CharField(label='next', widget=forms.HiddenInput(), required=False)


class LeagueSignupForm(forms.Form):
    kgs_username = forms.CharField(max_length=10, required=False)
    ogs_username = forms.CharField(max_length=40, required=False)
    egf_id = forms.IntegerField(label='European Go Federation ID (optional)', required=False)
    timezone = forms.ChoiceField(
        label='Time Zone (optional)',
        choices=[(t, t) for t in pytz.common_timezones],
        required=False,
        initial='UTC'
    )

    def __init__(self, *args, **kwargs):
        super(LeagueSignupForm, self).__init__(*args, **kwargs)
        communities = Community.objects.filter(private=False)
        choices = [(community.pk, community.name) for community in communities]
        self.fields["communities"] = forms.MultipleChoiceField(
            label="Communities (optional)",
            choices=choices,
            required=False,
            widget=Community_select
        )

    def clean_egf_id(self):
        if not self.cleaned_data['egf_id']:
            return ''
        egf_id = self.cleaned_data['egf_id']
        if Profile.objects.filter(egf_id=egf_id).exists():
            self.add_error('egf_id', "This EGF ID is already used by one of our member. You should contact us.")
        egf_rank = get_egf_rank(egf_id)
        if egf_rank is None:
            self.add_error('egf_id', 'This EGF ID seems invalid.')
        return egf_id

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
        if self.cleaned_data['communities']:
            communities = Community.objects.filter(pk__in=self.cleaned_data['communities'])
            for community in communities:
                user.groups.add(community.new_user_group)
        user.save()
        profile = Profile(
            user=user,
            timezone=self.cleaned_data['timezone']
        )
        if self.cleaned_data['kgs_username']:
            profile.kgs_username = self.cleaned_data['kgs_username']
        if self.cleaned_data['ogs_username']:
            profile.ogs_username = self.cleaned_data['ogs_username']
            id = get_user_id(self.cleaned_data['ogs_username']) # we do an extra request after clean. We should store.
            profile.ogs_id = id
            if id > 0:
                profile.ogs_rank = get_user_rank(id)
        if self.cleaned_data['egf_id']:
            profile.egf_id = self.cleaned_data['egf_id']
            profile.egf_rank = get_egf_rank(self.cleaned_data['egf_id'])
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
        widgets = {
            'name':forms.TextInput(),
        }

class LeagueEventForm(forms.ModelForm):
    begin_time = forms.DateField(
        input_formats=['%d/%m/%Y'],
        widget=forms.DateInput(format='%d/%m/%Y'),
        help_text="UTC time at 00:00. Format: dd/mm/yyyy"
    )
    end_time = forms.DateField(
        input_formats=['%d/%m/%Y'],
        widget=forms.DateInput(format='%d/%m/%Y'),
        help_text="Set it to the 1st to have full month."
    )

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
            'max_handicap',
            'min_handicap',
            'rules_type',
            'clock_type',
            'main_time',
            'additional_time',
            'is_open',
            'is_public',
            'self_join',
            'is_primary',
            'description',
            'prizes',
            'additional_informations',
            'community',
            'servers'
        ]
        # Customise year list to show 2 years in the past/future
        #EVENT_YEAR_CHOICES = range(datetime.date.today().year - 2, datetime.date.today().year + 3)
        widgets = {
            'name': forms.TextInput(),
            'community': forms.HiddenInput()
        }
        help_texts = {
            'name': "Name of the league",
            'event_type': 'League will work',
            'nb_matchs': 'Maximum number of match two players can play together',
            'ppwin': 'Point per win',
            'pploss': 'Point per loss',
            'main_time': 'The minimum starting time of the clock.',
            'additional_time': "If byoyomi, user will have a minimum 3 x this time byoyomi.\
                If Fischer, it's the additional time per move",
            'min_matchs': 'Minimum of match for a user to be considered active',
            'is_open': 'Can people register and game get scraped?',
            'is_public': 'Can people see the league?',
            'is_primary': 'A primary league will automatically be joined when joining another league.',
            'self_join': 'If checked people will be able to join the league by themselves',
            'komi': 'Valid komi for even games of the league. For handicap games, the valid komi is always 0.5',
            'max_handicap': 'Games handicap must be lower or equal.',
            'min_handicap': 'Games handicap must be greater or equal.',
            'additional_informations': 'This will be shown in the infos tab of the league.',
            'servers': 'Comma seperated list of Go servers from "KGS", "OGS" and "Goquest".'
        }

    def clean(self):
        '''convert replace timezones to utc'''
        cleaned_data = self.cleaned_data
        cleaned_data['begin_time'] = make_aware(
            datetime.datetime.combine(
                cleaned_data['begin_time'],
                datetime.time()
            ),
            pytz.utc
        )
        cleaned_data['end_time'] = make_aware(
            datetime.datetime.combine(
                cleaned_data['end_time'],
                datetime.time()
            ),
            pytz.utc
        )
        return cleaned_data


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
            'egf_id',
            'egf_rank',
            'ffg_licence_number',
            'ffg_rank',
            'country',
            'go_quest_username'
        ]
        widgets = {'country': CountrySelectWidget()}

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.egf_rank_cache = None
        self.ffg_rank_cache = None
        # prevent user from updating their EGF id if it's allready set
        if Profile.objects.get(pk=self.instance.pk).egf_id:
            self.fields['egf_id'].disabled = True
        if Profile.objects.get(pk=self.instance.pk).ffg_licence_number and \
            Profile.objects.get(pk=self.instance.pk).ffg_licence_number != "0":
            self.fields['ffg_licence_number'].disabled = True

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
        return go_quest_username

    def clean_egf_id(self):
        if not self.cleaned_data['egf_id']:
            return None
        egf_id = self.cleaned_data['egf_id']
        # Check if this ID is already used
        if Profile.objects.filter(egf_id=egf_id).exclude(pk=self.instance.pk).exists():
            self.add_error(
                'egf_id',
                "This EGF ID is already used by one of our member. You should contact us."
            )
        # check if ID is valid and get rank
        egf_rank = get_egf_rank(egf_id)
        if egf_rank is None:
            self.add_error('egf_id', 'This EGF ID seems invalid.')
        else:
            # store egf_rank to avoid extra api call later at clean
            self.egf_rank_cache = egf_rank
        return egf_id

    def clean_ffg_licence_number(self):
        if not self.cleaned_data['ffg_licence_number']:
            return None
        ffg_licence_number = self.cleaned_data['ffg_licence_number']
        if Profile.objects.filter(ffg_licence_number=ffg_licence_number).exclude(pk=self.instance.pk).exists():
            self.add_error(
                'ffg_licence_number',
                "This FFG Licence number is already used by one of our member. You should contact us."
            )
        # check if ID is valid and get rank
        ffg_rank = get_ffg_rank(ffg_licence_number)
        if ffg_rank is None:
            self.add_error('ffg_licence_number', 'This FFG licence number seems invalid')
        else:
            # store egf_rank to avoid extra api call later at clean
            self.ffg_rank_cache = ffg_rank
        return ffg_licence_number

    def clean(self):
        super(ProfileForm, self).clean()
        if self.egf_rank_cache is not None:
            self.cleaned_data['egf_rank'] = self.egf_rank_cache
        if self.ffg_rank_cache is not None:
            self.cleaned_data['ffg_rank'] = self.ffg_rank_cache
        if not (self.cleaned_data['kgs_username'] or self.cleaned_data['ogs_username']):
            self.add_error('kgs_username', '')
            self.add_error('ogs_username', '')
            raise forms.ValidationError("You should enter OGS or KGS username")
        return self.cleaned_data
