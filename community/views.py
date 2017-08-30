from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import UpdateView, CreateView
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import user_passes_test, login_required
from league.models import is_league_admin
from .models import Community
from .forms import CommunityForm

@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_community_list(request):
    communitys = Community.objects.all()
    return render(request, 'community/admin/community_list.html', {'communitys': communitys})

@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_community_create(request):
    if request.method == 'POST':
        form = CommunityForm(request.POST)
        if form.is_valid():
            community = Community.create(form.cleaned_data['name'])
            community.save()
            return HttpResponseRedirect(reverse('community:admin_community_list'))
    else:
        form = CommunityForm
        return render(request, 'community/admin/community_create.html', {'form': form})


class CommunityUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = CommunityForm
    model = Community
    template_name_suffix = '_update'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated() and user.user_is_league_admin()

    def get_login_url(self):
        return '/'

@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
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
    leagues = community.communityleague_set
    context = {
        'community': community,
        'leagues': leagues,
    }
    return render(request, 'community/community_page.html', context)
