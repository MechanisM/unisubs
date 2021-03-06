# Universal Subtitles, universalsubtitles.org
#
# Copyright (C) 2011 Participatory Culture Foundation
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

import json

from django.conf import settings
from haystack.indexes import *
from haystack.query import SearchQuerySet
from haystack.backends import SQ
from haystack import site

from teams import models
from apps.teams.moderation import WAITING_MODERATION
from apps.videos.models import SubtitleLanguage
from icanhaz.models import VideoVisibilityPolicy


LANGUAGES_DICT = dict(settings.ALL_LANGUAGES)


class TeamVideoLanguagesIndex(SearchIndex):
    text = CharField(
        document=True, use_template=True,
        template_name="teams/teamvideo_languages_for_search.txt")
    team_id = IntegerField()
    team_video_pk = IntegerField(indexed=False)
    video_pk = IntegerField(indexed=False)
    video_id = CharField(indexed=False)
    video_title = CharField(faceted=True)
    video_url = CharField(indexed=False)
    original_language = CharField()
    original_language_display = CharField(indexed=False)
    has_lingua_franca = BooleanField()
    absolute_url = CharField(indexed=False)
    project_pk = IntegerField(indexed=True)
    task_count = IntegerField()
    # never store an absolute url with solr
    # since the url changes according to the user
    # one cannot construct the url at index time
    # video_absolute_url = CharField(indexed=False)
    thumbnail = CharField(indexed=False)
    title = CharField()
    project_name = CharField(indexed=False)
    project_slug = CharField(indexed=False)
    description = CharField(indexed=False)
    is_complete = BooleanField()
    video_complete_date = DateTimeField(null=True)
    # list of completed language codes
    video_completed_langs = MultiValueField()
    # list of completed language absolute urls. should have 1-1 mapping to video_compelted_langs
    video_completed_lang_urls = MultiValueField(indexed=False)

    needs_moderation = BooleanField()
    latest_submission_date = DateTimeField(null=True)
    team_video_create_date = DateTimeField()

    moderation_languages_names = MultiValueField(null=True)
    moderation_languages_pks = MultiValueField(null=True)
    # we'll serialize data from versions here -> links and usernames
    # that will be on the appgove all for that language
    moderation_version_info = CharField(indexed=False)

    # possible values for visibility:
    # is_public=True anyone can see
    # is_public=False and owned_by_team_id=None -> a regular user owns, no teams can list this video
    # is_public=False and owned_by_team_id=X -> only team X can see this video
    is_public = BooleanField()
    owned_by_team_id = IntegerField(null=True)

    num_completed_subs = IntegerField()

    def prepare(self, obj):
        self.prepared_data = super(TeamVideoLanguagesIndex, self).prepare(obj)
        self.prepared_data['team_id'] = obj.team.id
        self.prepared_data['team_video_pk'] = obj.id
        self.prepared_data['video_pk'] = obj.video.id
        self.prepared_data['video_id'] = obj.video.video_id
        self.prepared_data['video_title'] = obj.video.title
        self.prepared_data['video_url'] = obj.video.get_video_url()
        original_sl = obj.video.subtitle_language()
        if original_sl:
            self.prepared_data['original_language_display'] = \
                original_sl.get_language_display()
            self.prepared_data['original_language'] = original_sl.language
        else:
            self.prepared_data['original_language_display'] = ''
            self.prepared_data['original_language'] = ''
        self.prepared_data['has_lingua_franca'] = \
            bool(set(settings.LINGUA_FRANCAS) &
                 set([sl.language for sl in
                      obj.video.subtitlelanguage_set.all() if
                      sl.is_dependable()]))
        self.prepared_data['absolute_url'] = obj.get_absolute_url()
        self.prepared_data['thumbnail'] = obj.get_thumbnail()
        self.prepared_data['title'] = unicode(obj)
        self.prepared_data['description'] = obj.description
        self.prepared_data['is_complete'] = obj.video.complete_date is not None
        self.prepared_data['video_complete_date'] = obj.video.complete_date
        self.prepared_data['project_pk'] = obj.project.pk
        self.prepared_data['project_name'] = obj.project.name
        self.prepared_data['project_slug'] = obj.project.slug
        self.prepared_data['team_video_create_date'] = obj.created

        completed_sls = obj.video.completed_subtitle_languages()
        self.prepared_data['num_completed_subs'] = len(completed_sls)

        self.prepared_data['video_completed_langs'] = \
            [sl.language for sl in completed_sls]
        self.prepared_data['video_completed_lang_urls'] = \
            [sl.get_absolute_url() for sl in completed_sls]

        self.prepared_data['task_count'] = models.Task.objects.incomplete().filter(team_video=obj).count()

        policy = obj.video.policy
        owned_by = None
        if policy and policy.belongs_to_team:
            owned_by = policy.object_id

        self.prepared_data['is_public'] =  VideoVisibilityPolicy.objects.video_is_public(obj.video)
        self.prepared_data["owned_by_team_id"] = owned_by

        self.prepares_moderation_info( obj, self.prepared_data)
        return self.prepared_data

    def prepares_moderation_info(self, obj, prepared_data):
        mod_on_same_team =  obj.video.moderated_by == obj.team
        on_mod = obj.team.get_pending_moderation().filter(language__video=obj.video).count() > 0
        self.prepared_data["needs_moderation"] =  mod_on_same_team and on_mod

        self.moderation_languages_urls = []
        self.moderation_languages_names = []
        self.moderation_version_info = ""

        pending_versions = obj.team.get_pending_moderation()
        pending_languages = list(SubtitleLanguage.objects.filter(video=obj.video,
                                                            subtitleversion__moderation_status=WAITING_MODERATION).distinct("language"))
        if len(pending_languages) == 0 or self.prepared_data["needs_moderation"] is False:
            return

        prepared_data['moderation_languages_names'] =  []
        prepared_data['moderation_languages_pks'] =  []
        moderation_version_info = []
        for lang in pending_languages:
            prepared_data['moderation_languages_names'].append(lang.language)
            prepared_data['moderation_languages_pks'].append(lang.pk)
            versions = pending_versions.filter(language=lang)
            version_info = []
            for version in versions:
                version_info.append({
                        "username":version.user and version.user.username,
                        "user_id": version.user and version.user.pk,
                        "pk":version.pk
                })
            moderation_version_info.append( version_info)
        self.prepared_data["latest_submission_date"] = pending_versions.order_by("-datetime_started")[0].datetime_started
        self.prepared_data['moderation_version_info'] = json.dumps(moderation_version_info)



    @classmethod
    def results_for_members(self, team):
        base_qs = SearchQuerySet().models(models.TeamVideo)
        public = SQ(is_public=True)
        mine = SQ(is_public=False,  owned_by_team_id=team.pk)
        return base_qs.filter(public | mine)


    @classmethod
    def results(self):
        return SearchQuerySet().models(models.TeamVideo).filter(is_public=True)


site.register(models.TeamVideo, TeamVideoLanguagesIndex)
