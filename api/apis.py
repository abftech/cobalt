"""These are the supported APIs for Cobalt.

Authentication is handled in the urls.py module, so by the time you get here you are dealing
with an authenticated user. Functions in here are still responsible for rbac calls to
handle access.

Code here should be as short as possible, if anything more complex is required you should
call a function in the 'home' module for the thing you are doing.

APIs should all be versioned with /vx.y at the end of the URI. This is automatically logged
every time an API is called.

APIs should all return JSON with at least one parameter e.g.

    {'status': 'Success'}

    or

    {'status: 'Failure'}

    or

    {'status: 'Access Denied'}

"""
from ninja import Router, File, NinjaAPI, Schema
from ninja.files import UploadedFile

from api.core import api_rbac
from notifications.apis import notifications_api_sms_file_upload_v1


class ErrorV1(Schema):
    """Standard error format"""

    status: str
    message: str


class UnauthorizedV1(Schema):
    """Standard error format"""

    detail: str


router = Router()
api = NinjaAPI()


@router.get("/keycheck/v1.0")
def key_check_v1(request):
    """Allow a developer to check that their key is valid"""
    return f"Your key is valid. You are authenticated as {request.auth}."


class SmsResponseV1(Schema):
    """Success response format from sms_file_upload"""

    status: str
    sender: str
    filename: str
    attempted: int
    sent: int


@router.post(
    "/sms-file-upload/v1.0",
    response={200: SmsResponseV1, 401: UnauthorizedV1, 403: ErrorV1},
    summary="SMS file upload API for distribution of different messages to a list of players.",
)
def sms_file_upload_v1(request, file: UploadedFile = File(...)):
    """Allow scorers to upload a file with ABF numbers and messages to send to members.

    File format is abf_number[tab character (\\t)]message

    The filename is used as the description.

    If the message contains \\<NL\\> then we change this to a newline (\\n).

    Messages over 140 characters will be sent as multiple SMSs.
    """

    # Check access
    role = "notifications.realtime_send.edit"
    status, return_error = api_rbac(request, role)
    if not status:
        return return_error

    return notifications_api_sms_file_upload_v1(request, file)
