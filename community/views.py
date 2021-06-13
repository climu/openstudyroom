from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import UpdateView
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_exempt
from league.models import User, LeagueEvent, Sgf
from league.views import LeagueEventCreate, LeagueEventUpdate
from league.forms import ActionForm
from tournament.views import TournamentCreate
from fullcalendar.views import PublicEventCreate, CategoryCreate
from .models import Community
from .forms import CommunityForm, AdminCommunityForm, CommunytyUserForm


@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def admin_community_list(request):
    communitys = Community.objects.all()
    return render(request, 'community/admin/community_list.html', {'communitys': communitys})


@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def admin_community_create(request):
    if request.method == 'POST':
        form = AdminCommunityForm(request.POST)
        if form.is_valid():
            community = Community.create(
                form.cleaned_data['name'],
                form.cleaned_data['slug']
            )
            community.save()
            return HttpResponseRedirect(reverse('community:admin_community_list'))
    else:
        form = AdminCommunityForm
    return render(request, 'community/admin/community_create.html', {'form': form})


class AdminCommunityUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = AdminCommunityForm
    model = Community
    template_name_suffix = '_admin_update'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_osr_admin()

    def get_login_url(self):
        return '/'


class CommunityUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = CommunityForm
    model = Community
    template_name_suffix = '_update'

    def get_success_url(self):
        return reverse(
            'community:community_page',
            kwargs={'slug': self.get_object().slug}
        )

    def test_func(self):
        user = self.request.user
        return self.get_object().is_admin(user)

    def get_login_url(self):
        return '/'


@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def admin_community_delete(request, pk):
    community = get_object_or_404(Community, pk=pk)
    if request.method == 'POST':
        admin_group = community.admin_group
        user_group = community.user_group
        community.delete()
        admin_group.delete()
        if user_group is not None:
            user_group.delete()
        return HttpResponseRedirect(reverse('community:admin_community_list'))

    else:
        raise Http404('What are you doing here?')


def community_page(request, slug):
    """ Main community view.

    Shows community descriptions, leagues, tournaments, members and games.
    """

    community = get_object_or_404(Community, slug=slug)

    if community.private and not community.is_member(request.user):
        raise Http404('What are you doing here?')

    # check rights
    admin = community.is_admin(request.user)
    # we should have a can_join method
    can_join = request.user.is_authenticated and \
        request.user.is_league_member() and \
        not community.is_member(request.user) and \
        not community.close

    # get leagues and tournaments
    leagues = community.leagueevent_set.all()
    if not admin:
        leagues = leagues.filter(is_public=True)
    tournaments = leagues.filter(event_type='tournament')
    leagues = leagues.exclude(event_type='tournament')

    # get members
    members = User.objects.filter(groups=community.user_group).select_related('profile')
    admins = members.filter(groups=community.admin_group)
    new_members = User.objects.\
        filter(groups=community.new_user_group).\
        filter(groups__name='league_member').\
        select_related('profile').\
        prefetch_related('discord_user')

    # get game records
    sgfs = Sgf.objects.defer('sgf_text').\
        filter(league_valid=True, events__in=leagues).\
        exclude(winner__isnull=True).\
        select_related('white', 'white__profile', 'black', 'black__profile', 'winner').\
        prefetch_related("white__discord_user", "black__discord_user").\
        distinct().\
        order_by('-date')

    # get calendar data
    calendar_data = {}
    calendar_data['community'] = community.format()
    if request.user.is_authenticated:
        calendar_data['user'] = request.user.format()

    context = {
        'community': community,
        'leagues': leagues,
        'tournaments': tournaments,
        'sgfs': sgfs,
        'admin': admin,
        'can_join': can_join,
        'can_quit': community.user_group in request.user.groups.all(),
        'members': members,
        'admins': admins,
        'new_members': new_members,
        'start_time_range': request.user.profile.start_cal if request.user.is_authenticated else 0,
        'end_time_range':  request.user.profile.end_cal if request.user.is_authenticated else 0,
        'public_events': community.publicevent_set.all(),
        'categories': community.category_set.all(),
        'calendar_data': calendar_data,
    }
    return render(request, 'community/community_page.html', context)


def community_list(request):
    groups = request.user.groups.all()
    communitys = Community.objects.filter(Q(private=False)|Q(user_group__in=groups))
    return render(
        request,
        'community/community_list.html',
        {'communitys': communitys}
    )


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def community_join(request, community_pk, user_pk):
    community = get_object_or_404(Community, pk=community_pk)
    user = get_object_or_404(User, pk=user_pk)
    if not community.is_admin(request.user) and (
        not user == request.user or community.close
    ):
        raise Http404('what are you doing here')

    if request.method == 'POST':
        user.groups.add(community.user_group)
        message = "You just join the " + community.name + " community."
        messages.success(request, message)
        return HttpResponseRedirect(reverse(
            'community:community_page',
            kwargs={'slug': community.slug}
        ))
    else:
        raise Http404('what are you doing here ?')


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def community_quit(request, community_pk, user_pk):
    community = get_object_or_404(Community, pk=community_pk)
    user = get_object_or_404(User, pk=user_pk)
    if not community.is_admin(request.user) and user != request.user:
        raise Http404('what are you doing here')
    if request.method == 'POST':
        user.groups.remove(community.user_group)
        user.groups.remove(community.new_user_group)
        if user == request.user:
            message = "You just quit the " + community.name + " community."
            messages.success(request, message)
            if community.private:
                return HttpResponseRedirect(reverse(
                    'community:community_list',
                ))
            else:
                return HttpResponseRedirect(reverse(
                    'community:community_page',
                    kwargs={'slug': community.slug}
                ))
        else:
            message = user.username + " is not in your community anymore."
            messages.success(request, message)
            return HttpResponseRedirect(reverse(
                'community:community_page',
                kwargs={'slug': community.slug}
            ))
    else:
        raise Http404('what are you doing here ?')


def community_results_page(request, slug):
    """Redirect to the last community open league results page"""
    community = get_object_or_404(Community, slug=slug)
    league = LeagueEvent.objects.filter(
        community=community,
        is_open=True
    ).order_by('end_time').first()
    return HttpResponseRedirect(reverse(
        'league:results',
        kwargs={'event_id': league.pk})
    )


@login_required()
def admin_user_list(request, pk):
    """allow admin to manage the users of a community. Usefull for close ones."""
    community = get_object_or_404(Community, pk=pk)
    if not community.is_admin(request.user):
        raise Http404('what are you doing here')
    community_users = User.objects.filter(groups=community.user_group)
    return render(
        request,
        'community/admin/user_list.html',
        {'community': community, 'community_users': community_users}
    )


@require_POST
@login_required()
def admin_invite_user(request, pk):
    """Invite a user in a community."""
    community = get_object_or_404(Community, pk=pk)
    if not community.is_admin(request.user):
        raise Http404('what are you doing here')
    form = CommunytyUserForm(request.POST)
    message = "Oups! Something went wrong."
    if form.is_valid():
        user = User.objects.get(username__iexact=form.cleaned_data['username'])
        if user.is_league_member():
            user.groups.add(community.user_group)
            user.groups.remove(community.new_user_group)
            # group = Group.objects.get(name='league_member')/
            # user.groups.add(group)
            message = user.username +" is now a member of your community."
    messages.success(request, message)
    return HttpResponseRedirect(reverse(
        'community:community_page',
        kwargs={'slug': community.slug}
    ))


@login_required()
def manage_admins(request, pk):
    community = get_object_or_404(Community, pk=pk)
    if not community.is_admin(request.user):
        raise Http404('what are you doing here')
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            user = get_object_or_404(User, pk=form.cleaned_data['user_id'])
            group = community.admin_group
            if form.cleaned_data['action'] == "rm":
                group.user_set.remove(user)
                message = "Succesfully removed " + user.username + " from community admins."
            elif form.cleaned_data['action'] == "add":
                if user.is_league_member():
                    group.user_set.add(user)
                    message = "Succesfully added " + user.username + " to community admins."
                else:
                    message = user.username + "account has nor been validated yet"
            messages.success(request, message)
    return HttpResponseRedirect(reverse(
        'community:community_page',
        kwargs={'slug': community.slug}
    ))




class CommunityLeagueEventCreate(LeagueEventCreate):
    """subclass of LeagueEventCreate view for communitys"""

    def test_func(self):
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        return community.is_admin(self.request.user)

    def get_success_url(self):
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        return reverse(
                'community:community_page',
                kwargs={'slug': community.slug}
        )

    def form_valid(self, form):
        response = super(CommunityLeagueEventCreate, self).form_valid(form)
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        self.object.community = community
        self.object.save()
        return response

class CommunityLeagueEventUpdate(LeagueEventUpdate):
    def get_success_url(self):
        return reverse(
            'community:community_page',
            kwargs={'slug': self.get_object().community.slug}
        )

    def get_context_data(self, **kwargs):
        context = super(CommunityLeagueEventUpdate, self).get_context_data(**kwargs)
        league = self.get_object()
        context['other_events'] = league.get_other_events().filter(community=league.community)
        return context


class CommunityTournamentCreate(TournamentCreate):
    """subclass of TournamentCreate view for communitys"""
    def test_func(self):
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        return community.is_admin(self.request.user)

    def get_success_url(self):
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        return reverse(
            'community:community_page',
            kwargs={'slug': community.slug}
        )
    def form_valid(self, form):
        response = super(CommunityTournamentCreate, self).form_valid(form)
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        self.object.community = community
        self.object.save()
        return response


class CommunityEventCreate(PublicEventCreate):
    def test_func(self):
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        return community.is_admin(self.request.user)

    def get_success_url(self):
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        return reverse(
            'community:community_page',
            kwargs={'slug': community.slug}
        )
    def form_valid(self, form):
        response = super(CommunityEventCreate, self).form_valid(form)
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        self.object.community = community
        self.object.save()
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['community_pk'] = self.kwargs.get('community_pk')
        return kwargs

class CommunityCategoryCreate(CategoryCreate):
    def test_func(self):
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        return community.is_admin(self.request.user)

    def get_success_url(self):
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        return reverse(
            'community:community_page',
            kwargs={'slug': community.slug}
        )
    def form_valid(self, form):
        response = super(CommunityCategoryCreate, self).form_valid(form)
        community_pk = self.kwargs.get('community_pk')
        community = get_object_or_404(Community, pk=community_pk)
        self.object.community = community
        self.object.save()
        return response

@xframe_options_exempt
def calendar_iframe(request, slug):
    community = get_object_or_404(Community, slug=slug)

    if community.private and not community.is_member(request.user):
        raise Http404('What are you doing here?')
    return render(
        request,
        'community/calendar_iframe.html',
        {'community': community}
    )
