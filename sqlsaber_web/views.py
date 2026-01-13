from django.contrib.auth.decorators import login_required
from django.http import Http404
from inertia import render

from .models import Thread


@login_required
def home(request):
    return render(request, "Chat")


@login_required
def thread_list(request):
    """Render the threads list page."""
    return render(request, "ThreadList")


@login_required
def thread_detail(request, thread_id: int):
    """Render a specific thread detail page."""
    if not Thread.objects.filter(user=request.user, pk=thread_id).exists():
        raise Http404

    return render(request, "ThreadDetail", props={"threadId": thread_id})


@login_required
def settings_page(request):
    return render(request, "Settings")
