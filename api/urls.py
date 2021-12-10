"""This is the main entry point for the cobalt API. The API is a separate Django app as
this makes things cleaner and easier to manage than having the (relatively small) API code
spread across lots of modules."""

from django.urls import path
from ninja import NinjaAPI

from accounts.models import User, APIToken
from .apis import router as cobalt_router
from ninja.security import (
    APIKeyQuery,
    APIKeyHeader,
    APIKeyCookie,
    HttpBearer,
    HttpBasicAuth,
)


class AuthCheck:
    """This is the core authentication method. Other classes inherit from this and provide
    different ways to obtain the same key from the client."""

    def authenticate(self, request, key):
        """Returns the user associated with this key or None (invalid)"""
        api_key = APIToken.objects.filter(token=key).first()
        if api_key:
            return api_key.user


class QueryKey(AuthCheck, APIKeyQuery):
    """Get the key from the query"""

    pass


class HeaderKey(AuthCheck, APIKeyHeader):
    """Get the key from the header"""

    pass


# # Needs CSRF token. Look at later
# class CookieKey(AuthCheck, APIKeyCookie):
#     """Get the key from the cookie"""
#     pass


class BearerKey(AuthCheck, HttpBearer):
    """Get the key from the HttpBearer"""

    pass


class BasicAuthKey(HttpBasicAuth):
    """Get the key from basic Authentication. This one is a little different. Has userid and password"""

    def authenticate(self, request, username, password):
        if username == "key" and password == "secret":
            return password


app_name = "api"

api = NinjaAPI(
    urls_namespace=f"{app_name}:api",
    docs_url="/docs/",
    auth=[QueryKey(), HeaderKey(), BearerKey(), BasicAuthKey()],
)

# You can have multiple routers so if this gets too big it can be split up.
# We use an unnecessary namespace to make this easy to do later if required.
api.add_router("cobalt", cobalt_router)

urlpatterns = [
    path("", api.urls),
]
