# Universal Subtitles, universalsubtitles.org
# 
# Copyright (C) 2010 Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see 
# http://www.gnu.org/licenses/agpl-3.0.html.

from auth.models import CustomUser as User
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from profiles.forms import EditUserForm, SendMessageForm, UserLanguageFormset, EditAvatarForm
from django.contrib import messages
from django.utils import simplejson as json
from django.utils.translation import ugettext_lazy as _, ugettext
from utils.amazon import S3StorageError
from tastypie.models import ApiKey
from django.views.generic.simple import direct_to_template
from django.views.generic.list_detail import object_list
from videos.models import Video, Action, SubtitleLanguage
from django.conf import settings
from django.db.models import Q
from profiles.rpc import ProfileApiClass
from utils.rpc import RpcRouter
from utils.orm import LoadRelatedQuerySet
from django.shortcuts import get_object_or_404
rpc_router = RpcRouter('profiles:rpc_router', {
    'ProfileApi': ProfileApiClass()
})

VIDEOS_ON_PAGE = getattr(settings, 'VIDEOS_ON_PAGE', 30) 

@login_required
def remove_avatar(request):
    if request.POST.get('remove'):
        request.user.picture = ''
        request.user.save()
    return HttpResponse(json.dumps({'avatar': request.user.avatar()}), "text/javascript")

@login_required
def edit_avatar(request):
    output = {}
    form = EditAvatarForm(request.POST, instance=request.user, files=request.FILES)
    if form.is_valid():
        try:        
            user = form.save()
            output['url'] =  str(user.avatar())
        except S3StorageError:
            output['error'] = {'picture': ugettext(u'File server unavailable. Try later. You can edit some other information without any problem.')}
        
    else:
        output['error'] = form.get_errors()
    return HttpResponse('<textarea>%s</textarea>'  % json.dumps(output))

class OptimizedQuerySet(LoadRelatedQuerySet):
    
    def update_result_cache(self):
        videos = dict((v.id, v) for v in self._result_cache if not hasattr(v, 'langs_cache'))
        
        if videos:
            for v in videos.values():
                v.langs_cache = []
                
            langs_qs = SubtitleLanguage.objects.select_related('video').filter(video__id__in=videos.keys())
            
            for l in langs_qs:
                videos[l.video_id].langs_cache.append(l)

@login_required
def dashboard(request):
    user = request.user
    context = {
        'user_info': user,
        'action_list': Action.objects.for_user(user)[:5]
    }

    return direct_to_template(request, 'profiles/dashboard.html', context)

@login_required
def my_videos(request):
    user = request.user
    qs = user.videos.order_by('-edited')
    q = request.REQUEST.get('q')

    if q:
        qs = qs.filter(Q(title__icontains=q)|Q(description__icontains=q))
    context = {
        'user_info': user,
        'my_videos': True,
        'query': q
    }
    qs = qs._clone(OptimizedQuerySet)

    return object_list(request, queryset=qs, 
                       paginate_by=VIDEOS_ON_PAGE, 
                       template_name='profiles/my_videos.html', 
                       extra_context=context, 
                       template_object_name='user_video')    

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = EditUserForm(request.POST,
                            instance=request.user,
                            files=request.FILES, label_suffix="")
        if form.is_valid():
            form.save()
            form_validated = True
        else:
            form_validated = False
            
        formset = UserLanguageFormset(request.POST, instance=request.user)
        if formset.is_valid() and form_validated:
            formset.save()
            messages.success(request, _('Your profile has been updated.'))
            return redirect('profiles:profile', user_id = request.user.username)
    else:
        form = EditUserForm(instance=request.user, label_suffix="")
        formset = UserLanguageFormset(instance=request.user)
    context = {
        'form': form,
        'user_info': request.user,
        'formset': formset,
        'edit_profile_page': True
    }
    return direct_to_template(request, 'profiles/edit_profile.html', context)

@login_required
def my_profile(request):

    return profile(request, user_id = request.user.id)

def profile(request, user_id=None):
    if user_id:
        try:
            user = User.objects.get(username=user_id)
        except User.DoesNotExist:
            try:
                user = User.objects.get(id=user_id)
            except (User.DoesNotExist, ValueError):
                raise Http404
    else:
        user = request.user
    context = {
        'user_info': user,
        'can_edit': user == request.user
    }
    return direct_to_template(request, 'profiles/view_profile.html', context)            

@login_required
def send_message(request):
    output = dict(success=False)
    form = SendMessageForm(request.user, request.POST)
    if form.is_valid():
        form.send()
        output['success'] = True
    else:
        output['errors'] = form.get_errors()
    return HttpResponse(json.dumps(output), "text/javascript")

@login_required
def actions_list(request):
    qs = Action.objects.for_user(request.user)
    extra_context = {
        'user_info': request.user
    }
                
    return object_list(request, queryset=qs, allow_empty=True,
                       paginate_by=settings.ACTIVITIES_ONPAGE,
                       template_name='profiles/actions_list.html',
                       template_object_name='action',
                       extra_context=extra_context)

@login_required
def generate_api_key(request):
    key, created = ApiKey.objects.get_or_create(user=request.user)
    if not created:
        key.key = key.generate_key()
        key.key = key.generate_key()
        key.save()
    return HttpResponse(json.dumps({"key":key.key}))
    
