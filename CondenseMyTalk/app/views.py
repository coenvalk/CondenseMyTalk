"""
Definition of views.
"""

from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime
from .forms import *
from .models import *

def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)

    lastvideo = Video.objects.last()
    if lastvideo:
        videofile = lastvideo.videofile
    else:
        videofile = ''

    # condensed_video = lastvideo.condense(0.75)

    return render(
        request,
        'app/index.html',
        {
            'title': lastvideo.name,
            'year': datetime.now().year,
            'videofile': videofile
        }
    )

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/contact.html',
        {
            'title':'Contact',
            'message':'Your contact page.',
            'year':datetime.now().year,
        }
    )

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/about.html',
        {
            'title':'About',
            'message':'Your application description page.',
            'year':datetime.now().year,
        }
    )

def video(request, vid):
    """Renders a video page."""
    v = Video.objects.get(videoid=vid)

    form = ROIForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        print(obj)
        obj.video = v
        obj.save()

    return render(
        request,
        'app/video.html',
        {
            'title': v.name,
            'vid': vid,
            'message': v.uploader,
            'year': datetime.now().year,
            'videofile': v.videofile,
            'rois': v.regionofinterest_set.all(),
            'form': form
        }
    )

def condensed(request, vid):
    v = Video.objects.get(videoid=vid)
    vfile, ext = os.path.splitext(str(v.videofile))
    f = vfile + "_CONDENSED" + ext

    return render(
        request,
        'app/video.html',
        {
            'title': v.name,
            'vid': vid,
            'message': v.uploader,
            'year': datetime.now().year,
            'videofile': f
        }
    )

def upload(request):
    if request.user.is_authenticated:
        form = VideoForm(request.POST or None, request.FILES or None)

        if form.is_valid():
            obj = form.save(commit=False)
            obj.uploader = request.user
            obj.save()

        return render(
            request,
            'app/upload.html',
            {
                'title': 'Upload',
                'message': 'upload your video here',
                'year': datetime.now().year,
                'form': form,
            }
        )