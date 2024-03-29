from ninja import NinjaAPI

from rbac.core import rbac_user_has_role

api = NinjaAPI()


def api_rbac(request, role):
    """Check if API user has RBAC role"""

    from api.apis import APIStatus

    if not rbac_user_has_role(request.auth, role):
        message = f"{request.auth} does not have role {role}"
        json_payload = {"status": APIStatus.ACCESS_DENIED, "message": message}
        return False, api.create_response(request, json_payload, status=403)

    return True, None
