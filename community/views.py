from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import UpdateView
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import user_passes_test, login_required
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
            community = Community.create(form.cleaned_data['name'])
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
            kwargs={'name': self.get_object().name}
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

def community_page(request,name):
    community = get_object_or_404(Community,name=name)
    leagues = community.leagueevent_set.all()

    context = {
        'community': community,
        'leagues': leagues,
        'admin': community.is_admin(request.user)
    }
    return render(request, 'community/community_page.html', context)


@login_required()
def community_create_league(request,community_pk):
    community = get_object_or_404(Community,pk=community_pk)
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
                kwargs={'name': community.name}))
        else:
            form = LeagueEventForm
            return render(
                request,
                'community/create_league.html',
                {'community': community, 'form': form}
            )
