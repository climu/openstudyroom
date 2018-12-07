from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import UpdateView
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.db.models import Q

from league.models import User, LeagueEvent, Sgf
from league.views import LeagueEventCreate, LeagueEventUpdate
from tournament.views import TournamentCreate
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
    community = get_object_or_404(Community, slug=slug)
    if community.private and not community.is_member(request.user):
        raise Http404('What are you doing here?')
    leagues = community.leagueevent_set.all()
    tournaments = leagues.filter(event_type='tournament')
    leagues = leagues.exclude(event_type='tournament')
    admin = community.is_admin(request.user)
    if not admin:
        leagues = leagues.filter(is_public=True)
    sgfs = Sgf.objects.filter(league_valid=True, events__in=leagues).order_by('-date')

    can_join = request.user.is_authenticated and \
        request.user.is_league_member() and \
        not community.is_member(request.user) and \
        not community.close

    context = {
        'community': community,
        'leagues': leagues,
        'tournaments': tournaments,
        'sgfs': sgfs,
        'admin': community.is_admin(request.user),
        'can_join': can_join,
        'can_quit': community.user_group in request.user.groups.all()
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
                'community:admin_user_list',
                kwargs={'pk': community.pk}
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

@login_required()
def admin_invite_user(request, pk):
    """Invite a user in a community."""
    community = get_object_or_404(Community, pk=pk)
    if not community.is_admin(request.user):
        raise Http404('what are you doing here')
    if request.method == 'POST':
        form = CommunytyUserForm(request.POST)
        if form.is_valid():
            user = User.objects.get(username__iexact=form.cleaned_data['username'])
            user.groups.add(community.user_group)
            # group = Group.objects.get(name='league_member')/
            # user.groups.add(group)
            message = user.username +" is now a member of your community."
            messages.success(request, message)
        else:
            message = "We don't have such a user."
            messages.success(request, message)
        return HttpResponseRedirect(reverse(
            'community:admin_user_list',
            kwargs={'pk': community.pk}
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
        print("here")
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
