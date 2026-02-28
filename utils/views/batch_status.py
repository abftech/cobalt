from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render

from utils.models import BatchStatus
from utils.utils import cobalt_paginator


@user_passes_test(lambda u: u.is_superuser)
def batch_status_view(request):
    """Show batch job run history"""

    status_filter = request.GET.get("status", "")

    batch_runs = BatchStatus.objects.order_by("-run_date")
    if status_filter:
        batch_runs = batch_runs.filter(status=status_filter)

    things = cobalt_paginator(request, batch_runs, 20)

    # Build searchparams so pagination preserves the status filter
    searchparams = f"status={status_filter}&" if status_filter else ""

    return render(
        request,
        "utils/batch_status.html",
        {
            "things": things,
            "current_status": status_filter,
            "searchparams": searchparams,
        },
    )
