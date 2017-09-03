from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import UpdateView
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.models import Group
from league.models import User, LeagueEvent
from .models import Community
from .forms import CommunityForm, AdminCommunityForm
from league.forms import LeagueEventForm


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def admin_community_list(request):
    communitys = Community.objects.all()
    return render(request, 'community/admin/community_list.html', {'communitys': communitys})

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
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
        return user.is_authenticated() and user.is_league_admin()

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
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def admin_community_delete(request, pk):
    community = get_object_or_404(Community,pk=pk)
    if request.method == 'POST':
        admin_group = community.admin_group
        user_group = community.user_group
        community.delete()
        admin_group.delete()
        if user_group is not None:
            user_group.delete()
        return HttpResponseRedirect(reverse('community:admin_community_list'))

    else:
        raise(Http404('What are you doing here?'))


def community_page(request,slug):
    community = get_object_or_404(Community, slug=slug)
    leagues = community.leagueevent_set.all()
    admin = community.is_admin(request.user)
    can_join = request.user.is_authenticated() and \
        request.user.is_league_member() and \
        not community.is_member(request.user) and \
        not community.private
    if not admin:
        leagues = leagues.filter(is_public=True)
    context = {
        'community': community,
        'leagues': leagues,
        'admin': community.is_admin(request.user),
        'can_join': can_join,
        'can_quit': community.user_group in request.user.groups.all()
    }
    return render(request, 'community/community_page.html', context)

def community_list(request):
    communitys = Community.objects.all()
    return render(
        request,
        'community/community_list.html',
        {'communitys': communitys}
    )

@login_required()
def community_create_league(request, community_pk):
    community = get_object_or_404(Community, pk=community_pk)
    if not community.is_admin(request.user):
        raise(Http404('What are you doing here?'))
    else:
        if request.method == 'POST':
            league = LeagueEvent(community=community)
            form = LeagueEventForm(request.POST, instance=league)
            if form.is_valid:
                form.save()

            return HttpResponseRedirect(reverse(
                'community:community_page',
                kwargs={'slug': community.slug}))
        else:
            form = LeagueEventForm
            return render(
                request,
                'community/create_league.html',
                {'community': community, 'form': form}
            )


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def community_join(request, community_pk, user_pk):
    community = get_object_or_404(Community, pk=community_pk)
    user = get_object_or_404(User, pk=user_pk)
    # Only and admin can join another user
    if not community.is_admin(user) and (
        not user == request.user or community.close
    ):
        raise Http404('what are you doing here')

    if request.method == 'POST':
        request.user.groups.add(community.user_group)
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
    if not community.is_admin(user) and (
        not user == request.user or community.close
    ):
        raise Http404('what are you doing here')
    if request.method == 'POST':
        request.user.groups.remove(community.user_group)
        return HttpResponseRedirect(reverse(
            'community:community_page',
            kwargs={'slug': community.slug}
        ))
    else:
        raise Http404('what are you doing here ?')
