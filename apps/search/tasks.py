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

from celery.schedules import crontab
from celery.decorators import periodic_task
from django.core.management import call_command

from django.conf import settings

SEARCH_INDEXING_HOUR_STARTS = getattr(settings, "SEARCH_INDEXING_HOUR_STARTS", 0)

@periodic_task(run_every=crontab(minute=0, hour=SEARCH_INDEXING_HOUR_STARTS))
def update_search_index():
    call_command('update_index', verbosity=2)
