from unittest.mock import patch, MagicMock

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.urls import NoReverseMatch

from accounts.models import User
from accounts.views.core import _register_handle_valid_form
from tests.test_manager import CobaltTestManagerUnit


class AccountsRegistrationTests:
    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager

    def test_01_register_duplicate_system_number_redirects_to_login(self):
        """Registering with an ABF number that belongs to an existing active account
        should redirect to the login page, not raise a NoReverseMatch error."""

        # Build an unsaved User with alan's system number (no pk — simulates a new registration attempt)
        new_user = User(
            username=str(self.manager.alan.system_number),
            first_name="Duplicate",
            last_name="Person",
            email="duplicate@test.com",
        )

        mock_form = MagicMock()
        mock_form.save.return_value = new_user

        request = RequestFactory().post("/accounts/register")
        request.session = {}
        request._messages = FallbackStorage(request)

        try:
            with patch("accounts.views.core.replace_unregistered_user_with_real_user"):
                response = _register_handle_valid_form(mock_form, request)

            is_redirect_to_login = (
                response.status_code == 302 and "login" in response.url
            )
            self.manager.save_results(
                status=is_redirect_to_login,
                test_name="Register with existing system number redirects to login",
                test_description="When a user tries to register with an ABF number that already has an active account, the view should redirect to the login page (not raise NoReverseMatch).",
                output=f"HTTP {response.status_code}, URL={response.url!r}",
            )
        except NoReverseMatch as e:
            self.manager.save_results(
                status=False,
                test_name="Register with existing system number redirects to login",
                test_description="When a user tries to register with an ABF number that already has an active account, the view should redirect to the login page (not raise NoReverseMatch).",
                output=f"NoReverseMatch raised: {e}",
            )
