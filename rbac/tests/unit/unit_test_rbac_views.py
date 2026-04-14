import json

from django.urls import reverse

from rbac.models import (
    RBACGroup,
    RBACAdminGroup,
    RBACAdminUserGroup,
    RBACAdminTree,
    RBACAdminGroupRole,
    RBACUserGroup,
    RBACGroupRole,
    RBACAppModelAction,
)
from tests.test_manager import CobaltTestManagerUnit

# Namespace for test-created objects so they don't collide with real data
TEST_QUALIFIER = "testrbacviews"


def _setup_group_admin(alan, group):
    """Give alan admin rights over a specific RBACGroup.

    Creates (or reuses) an RBACAdminGroup, adds alan to it, and creates an
    RBACAdminTree entry covering the group's full name path so that
    rbac_user_is_group_admin returns True.

    Returns the admin group.
    """
    admin_group, _ = RBACAdminGroup.objects.get_or_create(
        name_qualifier=TEST_QUALIFIER,
        name_item="views_admin_group",
        defaults={"description": "Admin group for view tests", "created_by": alan},
    )
    RBACAdminUserGroup.objects.get_or_create(group=admin_group, member=alan)
    RBACAdminTree.objects.get_or_create(group=admin_group, tree=group.name)
    return admin_group


def _setup_role_admin(alan, admin_group, app, model, model_id=None):
    """Give alan admin rights over a specific role (app.model[.model_id])."""
    RBACAdminGroupRole.objects.create(
        group=admin_group,
        app=app,
        model=model,
        model_id=model_id,
    )


class RBACViewsTests:
    """Tests for view functions in rbac/views.py.

    Covers: view_screen, admin_menu, tree_screen, list_screen,
    list_roles_screen, list_members_screen, admin_tree_screen,
    role_view_screen, group_view, admin_group_view, rbac_admin,
    rbac_tests (GET and POST), group_create (GET), admin_group_create (GET),
    group_edit (admin check), admin_group_edit (admin check),
    group_delete (GET admin check, POST delete), admin_group_delete (GET).
    """

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        self.manager.login_test_client(manager.alan)

        # Grab an existing group and admin group for simple view tests
        self.any_group = RBACGroup.objects.first()
        self.any_admin_group = RBACAdminGroup.objects.first()

    # ------------------------------------------------------------------ #
    # Read-only GET views                                                   #
    # ------------------------------------------------------------------ #

    def test_01_view_screen(self):
        """view_screen (RBAC home) returns 200."""
        url = reverse("rbac:view_screen")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC view_screen",
            test_description="GET /rbac/ returns HTTP 200 for a logged-in user",
            output=f"HTTP {rc}",
        )

    def test_02_admin_menu(self):
        """admin_menu returns 200."""
        url = reverse("rbac:admin_menu")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC admin_menu",
            test_description="GET /rbac/admin-menu returns HTTP 200",
            output=f"HTTP {rc}",
        )

    def test_03_tree_screen(self):
        """tree_screen returns 200."""
        url = reverse("rbac:tree_screen")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC tree_screen",
            test_description="GET /rbac/tree returns HTTP 200",
            output=f"HTTP {rc}",
        )

    def test_04_list_screen(self):
        """list_screen returns 200."""
        url = reverse("rbac:list_screen")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC list_screen",
            test_description="GET /rbac/list returns HTTP 200",
            output=f"HTTP {rc}",
        )

    def test_05_list_roles_screen(self):
        """list_roles_screen returns 200."""
        url = reverse("rbac:list_roles_screen")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC list_roles_screen",
            test_description="GET /rbac/list-roles returns HTTP 200",
            output=f"HTTP {rc}",
        )

    def test_06_list_members_screen(self):
        """list_members_screen returns 200."""
        url = reverse("rbac:list_members_screen")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC list_members_screen",
            test_description="GET /rbac/list-members returns HTTP 200",
            output=f"HTTP {rc}",
        )

    def test_07_admin_tree_screen(self):
        """admin_tree_screen returns 200."""
        url = reverse("rbac:admin_tree_screen")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC admin_tree_screen",
            test_description="GET /rbac/admin/tree returns HTTP 200",
            output=f"HTTP {rc}",
        )

    def test_08_role_view_screen(self):
        """role_view_screen returns 200."""
        url = reverse("rbac:role_view_screen")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC role_view_screen",
            test_description="GET /rbac/role-view returns HTTP 200",
            output=f"HTTP {rc}",
        )

    def test_09_group_view(self):
        """group_view returns 200 for an existing group."""
        url = reverse("rbac:group_view", kwargs={"group_id": self.any_group.id})
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC group_view",
            test_description="GET /rbac/group/view/<id>/ returns HTTP 200",
            output=f"HTTP {rc} for group id={self.any_group.id}",
        )

    def test_10_admin_group_view(self):
        """admin_group_view returns 200 for an existing admin group."""
        url = reverse(
            "rbac:admin_group_view",
            kwargs={"group_id": self.any_admin_group.id},
        )
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC admin_group_view",
            test_description="GET /rbac/admin/group/view/<id>/ returns HTTP 200",
            output=f"HTTP {rc} for admin group id={self.any_admin_group.id}",
        )

    def test_11_rbac_admin(self):
        """rbac_admin returns 200."""
        url = reverse("rbac:rbac_admin")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC rbac_admin",
            test_description="GET /rbac/admin returns HTTP 200",
            output=f"HTTP {rc}",
        )

    # ------------------------------------------------------------------ #
    # rbac_tests view (GET and POST branches)                              #
    # ------------------------------------------------------------------ #

    def test_12_rbac_tests_get(self):
        """rbac_tests GET returns 200."""
        url = reverse("rbac:rbac_tests")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC rbac_tests GET",
            test_description="GET /rbac/tests returns HTTP 200",
            output=f"HTTP {rc}",
        )

    def test_13_rbac_tests_post_user_has_role(self):
        """rbac_tests POST user_has_role branch returns 200."""
        url = reverse("rbac:rbac_tests")
        data = {
            "id_user": str(self.manager.alan.id),
            "id_text": "forums.forum.view",
            "user_has_role": "1",
        }
        rc = self.manager.client.post(url, data).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC rbac_tests POST user_has_role",
            test_description="POST to rbac_tests with user_has_role exercises the role-check branch",
            output=f"HTTP {rc}",
        )

    def test_14_rbac_tests_post_user_has_role_explain(self):
        """rbac_tests POST user_has_role_explain returns 200."""
        url = reverse("rbac:rbac_tests")
        data = {
            "id_user": str(self.manager.alan.id),
            "id_text": "forums.forum.view",
            "user_has_role_explain": "1",
        }
        rc = self.manager.client.post(url, data).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC rbac_tests POST user_has_role_explain",
            test_description="POST to rbac_tests with user_has_role_explain exercises the explain branch",
            output=f"HTTP {rc}",
        )

    def test_15_rbac_tests_post_user_access_in_english(self):
        """rbac_tests POST user_access_in_english returns 200."""
        url = reverse("rbac:rbac_tests")
        data = {
            "id_user": str(self.manager.alan.id),
            "id_text": "",
            "user_access_in_english": "1",
        }
        rc = self.manager.client.post(url, data).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC rbac_tests POST user_access_in_english",
            test_description="POST to rbac_tests with user_access_in_english returns HTTP 200",
            output=f"HTTP {rc}",
        )

    def test_16_rbac_tests_post_user_blocked_for_model(self):
        """rbac_tests POST user_blocked_for_model returns 200."""
        url = reverse("rbac:rbac_tests")
        data = {
            "id_user": str(self.manager.alan.id),
            "id_text": "forums.forum.9.view",
            "user_blocked_for_model": "1",
        }
        rc = self.manager.client.post(url, data).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC rbac_tests POST user_blocked_for_model",
            test_description="POST to rbac_tests with user_blocked_for_model returns HTTP 200",
            output=f"HTTP {rc}",
        )

    def test_17_rbac_tests_post_user_allowed_for_model(self):
        """rbac_tests POST user_allowed_for_model returns 200 (uses a Block-default model)."""
        url = reverse("rbac:rbac_tests")
        # rbac_user_allowed_for_model raises ReferenceError for Allow-default models;
        # use orgs.org which has default Block.
        data = {
            "id_user": str(self.manager.alan.id),
            "id_text": "orgs.org.9.edit",
            "user_allowed_for_model": "1",
        }
        rc = self.manager.client.post(url, data).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC rbac_tests POST user_allowed_for_model",
            test_description="POST to rbac_tests with user_allowed_for_model returns HTTP 200",
            output=f"HTTP {rc}",
        )

    # ------------------------------------------------------------------ #
    # group_create / admin_group_create GET                                #
    # ------------------------------------------------------------------ #

    def test_18_group_create_get(self):
        """group_create GET returns 200."""
        url = reverse("rbac:group_create")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC group_create GET",
            test_description="GET /rbac/group/create returns HTTP 200 (shows the form)",
            output=f"HTTP {rc}",
        )

    def test_19_admin_group_create_get(self):
        """admin_group_create GET returns 200."""
        url = reverse("rbac:admin_group_create")
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC admin_group_create GET",
            test_description="GET /rbac/admin/group/create returns HTTP 200",
            output=f"HTTP {rc}",
        )

    # ------------------------------------------------------------------ #
    # group_edit / admin_group_edit — non-admin path returns 200          #
    # ------------------------------------------------------------------ #

    def test_20_group_edit_not_admin(self):
        """group_edit GET returns 200 with error message when user is not admin."""
        url = reverse("rbac:group_edit", kwargs={"group_id": self.any_group.id})
        response = self.manager.client.get(url)
        body = response.content.decode()
        self.manager.save_results(
            status=response.status_code == 200 and "not an admin" in body.lower(),
            test_name="RBAC group_edit non-admin",
            test_description="GET group_edit without admin rights returns 200 with an error message",
            output=f"HTTP {response.status_code}, 'not an admin' in body: {'not an admin' in body.lower()}",
        )

    def test_21_admin_group_edit_not_admin(self):
        """admin_group_edit GET returns 200 with error message when user is not a member."""
        url = reverse(
            "rbac:admin_group_edit",
            kwargs={"group_id": self.any_admin_group.id},
        )
        response = self.manager.client.get(url)
        body = response.content.decode()
        self.manager.save_results(
            status=response.status_code == 200 and "not an admin" in body.lower(),
            test_name="RBAC admin_group_edit non-admin",
            test_description="GET admin_group_edit without membership returns 200 with an error message",
            output=f"HTTP {response.status_code}, 'not an admin' in body: {'not an admin' in body.lower()}",
        )

    # ------------------------------------------------------------------ #
    # group_edit — admin path                                              #
    # ------------------------------------------------------------------ #

    def test_22_group_edit_as_admin(self):
        """group_edit GET returns 200 when user is the group admin."""
        test_group = RBACGroup.objects.create(
            name_qualifier=TEST_QUALIFIER,
            name_item="edit_test",
            description="Edit test group",
            created_by=self.manager.alan,
        )
        _setup_group_admin(self.manager.alan, test_group)

        url = reverse("rbac:group_edit", kwargs={"group_id": test_group.id})
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC group_edit as admin",
            test_description="GET group_edit when user is group admin returns HTTP 200",
            output=f"HTTP {rc}",
        )

    # ------------------------------------------------------------------ #
    # group_delete — GET (confirm page) and POST (actual delete)          #
    # ------------------------------------------------------------------ #

    def test_23_group_delete_not_admin(self):
        """group_delete GET returns 200 with error when user is not admin."""
        url = reverse("rbac:group_delete", kwargs={"group_id": self.any_group.id})
        response = self.manager.client.get(url)
        body = response.content.decode()
        self.manager.save_results(
            status=response.status_code == 200 and "not an admin" in body.lower(),
            test_name="RBAC group_delete non-admin",
            test_description="GET group_delete without admin rights returns 200 with an error message",
            output=f"HTTP {response.status_code}, 'not an admin' in body: {'not an admin' in body.lower()}",
        )

    def test_24_group_delete_as_admin(self):
        """group_delete GET shows confirm page; POST deletes and redirects."""
        test_group = RBACGroup.objects.create(
            name_qualifier=TEST_QUALIFIER,
            name_item="delete_test",
            description="Delete test group",
            created_by=self.manager.alan,
        )
        _setup_group_admin(self.manager.alan, test_group)
        group_id = test_group.id

        url = reverse("rbac:group_delete", kwargs={"group_id": group_id})

        # GET — confirm page
        get_rc = self.manager.client.get(url).status_code

        # POST — delete
        post_response = self.manager.client.post(url)
        post_rc = post_response.status_code
        still_exists = RBACGroup.objects.filter(pk=group_id).exists()

        self.manager.save_results(
            status=get_rc == 200 and post_rc in (302, 301) and not still_exists,
            test_name="RBAC group_delete as admin",
            test_description="GET group_delete shows confirm page; POST deletes and redirects",
            output=f"GET={get_rc}, POST={post_rc}, group_still_exists={still_exists}",
        )

    def test_25_admin_group_delete_not_admin(self):
        """admin_group_delete GET returns 200 with error when user is not admin."""
        url = reverse(
            "rbac:admin_group_delete",
            kwargs={"group_id": self.any_admin_group.id},
        )
        response = self.manager.client.get(url)
        body = response.content.decode()
        self.manager.save_results(
            status=response.status_code == 200 and "not an admin" in body.lower(),
            test_name="RBAC admin_group_delete non-admin",
            test_description="GET admin_group_delete without admin rights returns 200 with error",
            output=f"HTTP {response.status_code}, 'not an admin' in body: {'not an admin' in body.lower()}",
        )

    def test_26_admin_group_delete_as_admin_get(self):
        """admin_group_delete GET shows confirm page when user is admin."""
        test_admin_group = RBACAdminGroup.objects.create(
            name_qualifier=TEST_QUALIFIER,
            name_item="adm_del_test",
            description="Admin delete test group",
            created_by=self.manager.alan,
        )
        RBACAdminUserGroup.objects.create(
            group=test_admin_group, member=self.manager.alan
        )

        url = reverse(
            "rbac:admin_group_delete",
            kwargs={"group_id": test_admin_group.id},
        )
        rc = self.manager.client.get(url).status_code
        self.manager.save_results(
            status=rc == 200,
            test_name="RBAC admin_group_delete as admin GET",
            test_description="GET admin_group_delete when user is admin shows confirm page (HTTP 200)",
            output=f"HTTP {rc}",
        )

    def test_27_login_required_redirect(self):
        """Unauthenticated request to view_screen redirects to login."""
        self.manager.client.logout()
        url = reverse("rbac:view_screen")
        rc = self.manager.client.get(url).status_code
        self.manager.login_test_client(self.manager.alan)
        self.manager.save_results(
            status=rc in (302, 301),
            test_name="RBAC view_screen login required",
            test_description="GET view_screen without authentication redirects to login",
            output=f"HTTP {rc} (expected redirect)",
        )


class RBACAdminAjaxTests:
    """Tests for ajax view functions in rbac/ajax.py.

    Covers: group_to_user_ajax, group_to_action_ajax,
    rbac_get_action_for_model_ajax, rbac_add_user_to_group_ajax (success
    and access-denied paths), rbac_add_user_to_admin_group_ajax,
    rbac_add_role_to_group_ajax, rbac_delete_user_from_group_ajax,
    rbac_delete_role_from_group_ajax, rbac_add_role_to_admin_group_ajax,
    rbac_delete_user_from_admin_group_ajax,
    rbac_delete_role_from_admin_group_ajax, and invalid-method branches.
    """

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        self.manager.login_test_client(manager.alan)
        self.any_group = RBACGroup.objects.first()

    def _json_message(self, response):
        return json.loads(response.content)["data"]["message"]

    def _make_test_group_with_admin(self):
        """Create an RBACGroup that alan is group-admin for, plus a role on it."""
        test_group = RBACGroup.objects.create(
            name_qualifier=TEST_QUALIFIER,
            name_item=f"ajax_group_{RBACGroup.objects.filter(name_qualifier=TEST_QUALIFIER).count()}",
            description="Ajax test group",
            created_by=self.manager.alan,
        )
        admin_group = RBACAdminGroup.objects.create(
            name_qualifier=TEST_QUALIFIER,
            name_item=f"ajax_admin_{RBACAdminGroup.objects.filter(name_qualifier=TEST_QUALIFIER).count()}",
            description="Ajax admin group",
            created_by=self.manager.alan,
        )
        RBACAdminUserGroup.objects.create(group=admin_group, member=self.manager.alan)
        RBACAdminTree.objects.create(group=admin_group, tree=test_group.name)
        # Give role admin rights over testrbac.thing
        RBACAdminGroupRole.objects.create(
            group=admin_group, app=TEST_QUALIFIER, model="thing", model_id=None
        )
        return test_group, admin_group

    # ------------------------------------------------------------------ #
    # group_to_user_ajax / group_to_action_ajax                           #
    # ------------------------------------------------------------------ #

    def test_01_group_to_user_ajax(self):
        """group_to_user_ajax returns JSON 200."""
        url = reverse("rbac:group_to_user_ajax", kwargs={"group_id": self.any_group.id})
        response = self.manager.client.get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="RBAC group_to_user_ajax",
            test_description="GET group_to_user_ajax returns HTTP 200 with JSON",
            output=f"HTTP {response.status_code}",
        )

    def test_02_group_to_action_ajax(self):
        """group_to_action_ajax returns JSON 200."""
        url = reverse(
            "rbac:group_to_action_ajax", kwargs={"group_id": self.any_group.id}
        )
        response = self.manager.client.get(url)
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="RBAC group_to_action_ajax",
            test_description="GET group_to_action_ajax returns HTTP 200 with JSON",
            output=f"HTTP {response.status_code}",
        )

    # ------------------------------------------------------------------ #
    # rbac_get_action_for_model_ajax                                       #
    # ------------------------------------------------------------------ #

    def test_03_get_action_for_model_ajax(self):
        """rbac_get_action_for_model_ajax GET returns JSON 200."""
        url = reverse("rbac:rbac_get_action_for_model_ajax")
        response = self.manager.client.get(url, {"app": "forums", "model": "forum"})
        self.manager.save_results(
            status=response.status_code == 200,
            test_name="RBAC rbac_get_action_for_model_ajax",
            test_description="GET rbac_get_action_for_model_ajax with valid app/model returns HTTP 200",
            output=f"HTTP {response.status_code}",
        )

    def test_04_get_action_for_model_ajax_invalid_method(self):
        """rbac_get_action_for_model_ajax POST returns invalid-request JSON."""
        url = reverse("rbac:rbac_get_action_for_model_ajax")
        response = self.manager.client.post(url, {})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Invalid request",
            test_name="RBAC rbac_get_action_for_model_ajax invalid method",
            test_description="POST to rbac_get_action_for_model_ajax returns JSON with 'Invalid request'",
            output=f"msg={msg!r}",
        )

    # ------------------------------------------------------------------ #
    # rbac_add_user_to_group_ajax                                          #
    # ------------------------------------------------------------------ #

    def test_05_add_user_to_group_ajax_success(self):
        """rbac_add_user_to_group_ajax returns Success when user is group admin."""
        test_group, _ = self._make_test_group_with_admin()
        url = reverse("rbac:rbac_add_user_to_group_ajax")
        response = self.manager.client.get(
            url,
            {"member_id": str(self.manager.betty.id), "group_id": str(test_group.id)},
        )
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Success",
            test_name="RBAC rbac_add_user_to_group_ajax success",
            test_description="Group admin can add a user to their group via ajax",
            output=f"msg={msg!r}",
        )

    def test_06_add_user_to_group_ajax_access_denied(self):
        """rbac_add_user_to_group_ajax returns Access Denied when not group admin."""
        url = reverse("rbac:rbac_add_user_to_group_ajax")
        response = self.manager.client.get(
            url,
            {
                "member_id": str(self.manager.betty.id),
                "group_id": str(self.any_group.id),
            },
        )
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Access Denied",
            test_name="RBAC rbac_add_user_to_group_ajax access denied",
            test_description="Non-admin gets Access Denied when trying to add a user to a group",
            output=f"msg={msg!r}",
        )

    def test_07_add_user_to_group_ajax_invalid_method(self):
        """rbac_add_user_to_group_ajax POST returns Invalid request."""
        url = reverse("rbac:rbac_add_user_to_group_ajax")
        response = self.manager.client.post(url, {})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Invalid request",
            test_name="RBAC rbac_add_user_to_group_ajax invalid method",
            test_description="POST to rbac_add_user_to_group_ajax returns Invalid request",
            output=f"msg={msg!r}",
        )

    # ------------------------------------------------------------------ #
    # rbac_add_user_to_admin_group_ajax                                    #
    # ------------------------------------------------------------------ #

    def test_08_add_user_to_admin_group_ajax_success(self):
        """rbac_add_user_to_admin_group_ajax returns Success for admin of admin group."""
        _, admin_group = self._make_test_group_with_admin()
        url = reverse("rbac:rbac_add_user_to_admin_group_ajax")
        response = self.manager.client.get(
            url,
            {
                "member_id": str(self.manager.betty.id),
                "group_id": str(admin_group.id),
            },
        )
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Success",
            test_name="RBAC rbac_add_user_to_admin_group_ajax success",
            test_description="Admin group member can add another user to the admin group",
            output=f"msg={msg!r}",
        )

    def test_09_add_user_to_admin_group_ajax_invalid_method(self):
        """rbac_add_user_to_admin_group_ajax POST returns Invalid request."""
        url = reverse("rbac:rbac_add_user_to_admin_group_ajax")
        response = self.manager.client.post(url, {})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Invalid request",
            test_name="RBAC rbac_add_user_to_admin_group_ajax invalid method",
            test_description="POST to rbac_add_user_to_admin_group_ajax returns Invalid request",
            output=f"msg={msg!r}",
        )

    # ------------------------------------------------------------------ #
    # rbac_add_role_to_group_ajax                                          #
    # ------------------------------------------------------------------ #

    def test_10_add_role_to_group_ajax_success(self):
        """rbac_add_role_to_group_ajax returns Success when user has all rights."""
        test_group, _ = self._make_test_group_with_admin()
        url = reverse("rbac:rbac_add_role_to_group_ajax")
        response = self.manager.client.get(
            url,
            {
                "group_id": str(test_group.id),
                "app": TEST_QUALIFIER,
                "model": "thing",
                "model_id": "None",
                "action": "edit",
                "rule_type": "Allow",
            },
        )
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Success",
            test_name="RBAC rbac_add_role_to_group_ajax success",
            test_description="User with group admin + role admin rights can add a role to a group",
            output=f"msg={msg!r}",
        )

    def test_11_add_role_to_group_ajax_access_denied(self):
        """rbac_add_role_to_group_ajax returns Access Denied without rights."""
        url = reverse("rbac:rbac_add_role_to_group_ajax")
        response = self.manager.client.get(
            url,
            {
                "group_id": str(self.any_group.id),
                "app": "forums",
                "model": "forum",
                "model_id": "1",
                "action": "edit",
                "rule_type": "Allow",
            },
        )
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Access Denied",
            test_name="RBAC rbac_add_role_to_group_ajax access denied",
            test_description="Non-admin gets Access Denied when trying to add a role to a group",
            output=f"msg={msg!r}",
        )

    def test_12_add_role_to_group_ajax_invalid_method(self):
        """rbac_add_role_to_group_ajax POST returns Invalid request."""
        url = reverse("rbac:rbac_add_role_to_group_ajax")
        response = self.manager.client.post(url, {})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Invalid request",
            test_name="RBAC rbac_add_role_to_group_ajax invalid method",
            test_description="POST to rbac_add_role_to_group_ajax returns Invalid request",
            output=f"msg={msg!r}",
        )

    # ------------------------------------------------------------------ #
    # rbac_delete_user_from_group_ajax                                     #
    # ------------------------------------------------------------------ #

    def test_13_delete_user_from_group_ajax_success(self):
        """rbac_delete_user_from_group_ajax returns Success when user is group admin."""
        test_group, _ = self._make_test_group_with_admin()
        # Add betty to the group first
        RBACUserGroup.objects.create(group=test_group, member=self.manager.betty)
        url = reverse("rbac:rbac_delete_user_from_group_ajax")
        response = self.manager.client.get(
            url,
            {
                "member_id": str(self.manager.betty.id),
                "group_id": str(test_group.id),
            },
        )
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Success",
            test_name="RBAC rbac_delete_user_from_group_ajax success",
            test_description="Group admin can remove a user from their group via ajax",
            output=f"msg={msg!r}",
        )

    def test_14_delete_user_from_group_ajax_access_denied(self):
        """rbac_delete_user_from_group_ajax returns Access Denied without rights."""
        url = reverse("rbac:rbac_delete_user_from_group_ajax")
        # Use a group alan is not admin for
        non_admin_group = RBACGroup.objects.exclude(
            name_qualifier=TEST_QUALIFIER
        ).first()
        RBACUserGroup.objects.get_or_create(
            group=non_admin_group, member=self.manager.betty
        )
        response = self.manager.client.get(
            url,
            {
                "member_id": str(self.manager.betty.id),
                "group_id": str(non_admin_group.id),
            },
        )
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Access Denied",
            test_name="RBAC rbac_delete_user_from_group_ajax access denied",
            test_description="Non-admin gets Access Denied when trying to remove a user from a group",
            output=f"msg={msg!r}",
        )

    def test_15_delete_user_from_group_ajax_invalid_method(self):
        """rbac_delete_user_from_group_ajax POST returns Invalid request."""
        url = reverse("rbac:rbac_delete_user_from_group_ajax")
        response = self.manager.client.post(url, {})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Invalid request",
            test_name="RBAC rbac_delete_user_from_group_ajax invalid method",
            test_description="POST to rbac_delete_user_from_group_ajax returns Invalid request",
            output=f"msg={msg!r}",
        )

    # ------------------------------------------------------------------ #
    # rbac_delete_role_from_group_ajax                                     #
    # ------------------------------------------------------------------ #

    def test_16_delete_role_from_group_ajax_success(self):
        """rbac_delete_role_from_group_ajax returns Success when user has rights."""
        test_group, _ = self._make_test_group_with_admin()
        role = RBACGroupRole.objects.create(
            group=test_group,
            app=TEST_QUALIFIER,
            model="thing",
            model_id=None,
            action="edit",
            rule_type="Allow",
        )
        url = reverse("rbac:rbac_delete_role_from_group_ajax")
        response = self.manager.client.get(url, {"role_id": str(role.id)})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Success",
            test_name="RBAC rbac_delete_role_from_group_ajax success",
            test_description="User with role admin + group admin rights can delete a role from a group",
            output=f"msg={msg!r}",
        )

    def test_17_delete_role_from_group_ajax_invalid_method(self):
        """rbac_delete_role_from_group_ajax POST returns Invalid request."""
        url = reverse("rbac:rbac_delete_role_from_group_ajax")
        response = self.manager.client.post(url, {})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Invalid request",
            test_name="RBAC rbac_delete_role_from_group_ajax invalid method",
            test_description="POST to rbac_delete_role_from_group_ajax returns Invalid request",
            output=f"msg={msg!r}",
        )

    # ------------------------------------------------------------------ #
    # rbac_add_role_to_admin_group_ajax                                    #
    # ------------------------------------------------------------------ #

    def test_18_add_role_to_admin_group_ajax_success(self):
        """rbac_add_role_to_admin_group_ajax returns Success when user is role admin."""
        _, admin_group = self._make_test_group_with_admin()
        url = reverse("rbac:rbac_add_role_to_admin_group_ajax")
        response = self.manager.client.get(
            url,
            {
                "group_id": str(admin_group.id),
                "app": TEST_QUALIFIER,
                "model": "thing",
                "model_id": "None",
            },
        )
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Success",
            test_name="RBAC rbac_add_role_to_admin_group_ajax success",
            test_description="Role admin can add a role to an admin group",
            output=f"msg={msg!r}",
        )

    def test_19_add_role_to_admin_group_ajax_access_denied(self):
        """rbac_add_role_to_admin_group_ajax returns Access Denied without role admin rights."""
        # Create a fresh admin group that Alan is NOT an admin of
        fresh_admin_group = RBACAdminGroup.objects.create(
            name_qualifier=TEST_QUALIFIER,
            name_item=f"no_access_admin_{RBACAdminGroup.objects.filter(name_qualifier=TEST_QUALIFIER).count()}",
            description="Admin group Alan is not admin of",
            created_by=self.manager.betty,
        )
        url = reverse("rbac:rbac_add_role_to_admin_group_ajax")
        response = self.manager.client.get(
            url,
            {
                "group_id": str(fresh_admin_group.id),
                "app": "xyzzy",
                "model": "nonce",
                "model_id": "99999",
            },
        )
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Access Denied",
            test_name="RBAC rbac_add_role_to_admin_group_ajax access denied",
            test_description="Non-role-admin gets Access Denied when trying to add a role to an admin group",
            output=f"msg={msg!r}",
        )

    def test_20_add_role_to_admin_group_ajax_invalid_method(self):
        """rbac_add_role_to_admin_group_ajax POST returns Invalid request."""
        url = reverse("rbac:rbac_add_role_to_admin_group_ajax")
        response = self.manager.client.post(url, {})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Invalid request",
            test_name="RBAC rbac_add_role_to_admin_group_ajax invalid method",
            test_description="POST to rbac_add_role_to_admin_group_ajax returns Invalid request",
            output=f"msg={msg!r}",
        )

    # ------------------------------------------------------------------ #
    # rbac_delete_user_from_admin_group_ajax                               #
    # ------------------------------------------------------------------ #

    def test_21_delete_user_from_admin_group_ajax_success(self):
        """rbac_delete_user_from_admin_group_ajax returns Success for admin of group."""
        _, admin_group = self._make_test_group_with_admin()
        RBACAdminUserGroup.objects.create(group=admin_group, member=self.manager.betty)
        url = reverse("rbac:rbac_delete_user_from_admin_group_ajax")
        response = self.manager.client.get(
            url,
            {
                "member_id": str(self.manager.betty.id),
                "group_id": str(admin_group.id),
            },
        )
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Success",
            test_name="RBAC rbac_delete_user_from_admin_group_ajax success",
            test_description="Admin group member can remove another user from the admin group",
            output=f"msg={msg!r}",
        )

    def test_22_delete_user_from_admin_group_ajax_invalid_method(self):
        """rbac_delete_user_from_admin_group_ajax POST returns Invalid request."""
        url = reverse("rbac:rbac_delete_user_from_admin_group_ajax")
        response = self.manager.client.post(url, {})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Invalid request",
            test_name="RBAC rbac_delete_user_from_admin_group_ajax invalid method",
            test_description="POST to rbac_delete_user_from_admin_group_ajax returns Invalid request",
            output=f"msg={msg!r}",
        )

    # ------------------------------------------------------------------ #
    # rbac_delete_role_from_admin_group_ajax                               #
    # ------------------------------------------------------------------ #

    def test_23_delete_role_from_admin_group_ajax_success(self):
        """rbac_delete_role_from_admin_group_ajax returns Success for role admin."""
        _, admin_group = self._make_test_group_with_admin()
        role = RBACAdminGroupRole.objects.create(
            group=admin_group, app=TEST_QUALIFIER, model="thing", model_id=None
        )
        url = reverse("rbac:rbac_delete_role_from_admin_group_ajax")
        response = self.manager.client.get(url, {"role_id": str(role.id)})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Success",
            test_name="RBAC rbac_delete_role_from_admin_group_ajax success",
            test_description="Role admin can delete a role from an admin group",
            output=f"msg={msg!r}",
        )

    def test_24_delete_role_from_admin_group_ajax_access_denied(self):
        """rbac_delete_role_from_admin_group_ajax returns Access Denied without rights."""
        # Find an existing admin group role that alan is not admin for
        existing_role = RBACAdminGroupRole.objects.exclude(app=TEST_QUALIFIER).first()
        if existing_role is None:
            self.manager.save_results(
                status=True,
                test_name="RBAC rbac_delete_role_from_admin_group_ajax access denied",
                test_description="Skipped — no non-test admin group role found to use for access-denied check",
                output="No suitable existing role found; skipped.",
            )
            return
        url = reverse("rbac:rbac_delete_role_from_admin_group_ajax")
        response = self.manager.client.get(url, {"role_id": str(existing_role.id)})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Access Denied",
            test_name="RBAC rbac_delete_role_from_admin_group_ajax access denied",
            test_description="Non-role-admin gets Access Denied when trying to delete a role from an admin group",
            output=f"msg={msg!r}",
        )

    def test_25_delete_role_from_admin_group_ajax_invalid_method(self):
        """rbac_delete_role_from_admin_group_ajax POST returns Invalid request."""
        url = reverse("rbac:rbac_delete_role_from_admin_group_ajax")
        response = self.manager.client.post(url, {})
        msg = self._json_message(response)
        self.manager.save_results(
            status=msg == "Invalid request",
            test_name="RBAC rbac_delete_role_from_admin_group_ajax invalid method",
            test_description="POST to rbac_delete_role_from_admin_group_ajax returns Invalid request",
            output=f"msg={msg!r}",
        )
