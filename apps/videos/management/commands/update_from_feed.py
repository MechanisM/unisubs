from django.core.management.base import BaseCommand
from videos.models import VideoFeed

class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        print 'Run update_from_feed command'
        
        for feed in VideoFeed.objects.all():
            print '-------------------------'
            print feed.url
            print 'Checked new entries: ', feed.update()