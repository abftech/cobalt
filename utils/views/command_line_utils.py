import logging
import os
import pathlib
import subprocess
import uuid

import psutil
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.timezone import now
from psutil import NoSuchProcess

from rbac.decorators import rbac_check_role

logger = logging.getLogger("cobalt")

COMMANDS = {
    "auto_pay_batch": {
        "description": "Run the nightly auto pay script for memberships",
        "arguments": None,
    },
    "transfer_club_pp_balances": {
        "description": "Transfer club PP balances to Bridge Credits.",
        "arguments": "filename",
    },
    "remove_club_contacts": {
        "description": "Delete contacts for a club.",
        "arguments": "filename",
    },
    "remove_club_members": {
        "description": "Delete memberships for a club.",
        "arguments": "filename",
    },
}


def _check_process_is_running(pid):
    """helper to check if a given process is running, also gets rid of zombies"""

    # Check on process
    try:
        process = psutil.Process(pid)
    except NoSuchProcess:
        return False

    # See if still running
    running = process.status() == psutil.STATUS_RUNNING

    logger.info(f"Checking for process {pid} running. {running}")

    # Can get zombie process for some reason
    if process.status() == psutil.STATUS_ZOMBIE:
        process.terminate()

    return running


@rbac_check_role("system.admin.edit")
def command_line_utils(request):
    """hack to run command line utils through the web page - these should really all be changed into proper web pages"""
    # Get requested action, will be None first time we are called
    action = request.POST.get("action")

    # Validate to ensure only permitted commands can be run
    if action and action not in COMMANDS:
        return HttpResponse("Invalid action")

    # If we have an action then this is a request to run something
    if action:
        cmd = action
        if COMMANDS[action]["arguments"]:
            identifier = f"input_{action}"
            filename = request.POST.get(identifier)
            cmd = f"{cmd} /tmp/{filename}"

        # start process externally
        process = subprocess.Popen(
            f"./manage.py  {cmd} >& /tmp/out.txt",
            shell=True,
            stdin=None,
            stdout=None,
            stderr=None,
            close_fds=True,
        )

        logger.info(f"Started process: ./manage.py {cmd}")

        # Build response - we return a button
        response = render(
            request,
            "utils/command_line_utils_run_button_htmx.html",
            {"pid": process.pid, "action": action, "running": True},
        )

        # Trigger showing the log file on the web page
        response["HX-Trigger"] = f"""{{"show_log": {process.pid}}}"""

        return response

    # Blank page first time called
    return render(request, "utils/command_line_utils.html", {"commands": COMMANDS})


@rbac_check_role("system.admin.edit")
def command_line_utils_show_log_htmx(request):
    """Show the log file for running process"""

    pid = int(request.POST.get("pid"))

    running = _check_process_is_running(pid)

    log = pathlib.Path("/tmp/out.txt").read_text()

    logger.info(f"Reading logfile for {pid}")
    logger.info(log)

    return render(
        request,
        "utils/command_line_utils_show_log_htmx.html",
        {"log": log, "running": running, "pid": pid},
    )


@rbac_check_role("system.admin.edit")
def command_line_utils_check_process_running_button_htmx(request):
    """Check if a process is still running"""

    # Get values from POST
    pid = int(request.POST.get("pid"))
    action = request.POST.get("action")

    running = _check_process_is_running(pid)

    logger.info(f"Checking for button - {running}")

    return render(
        request,
        "utils/command_line_utils_run_button_htmx.html",
        {"pid": pid, "action": action, "running": running},
    )


@rbac_check_role("system.admin.edit")
def command_line_upload_csv(request):
    if request.method != "POST" or not request.FILES.get("csv_file"):
        return HttpResponse("<div class='text-danger'>No file uploaded.</div>")

    csv_file = request.FILES["csv_file"]

    # Generate unique filename
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{request.user.first_name}_{unique_id}.csv"

    # Save to /tmp directory
    save_path = os.path.join("/tmp", filename)
    with open(save_path, "wb") as f:
        for chunk in csv_file.chunks():
            f.write(chunk)

    # Return a simple HTMX-friendly response
    response = HttpResponse(
        f"<div class='text-success'>CSV uploaded successfully as <strong>{filename}</strong>.</div>"
    )

    # Send back the filename to add to the input fields
    response["HX-Trigger"] = f"""{{"set_filename": "{filename}"}}"""

    return response
