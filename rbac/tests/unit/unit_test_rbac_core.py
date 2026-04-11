from rbac.core import (
    allow_to_boolean,
    rbac_add_role_to_group,
    rbac_add_user_to_admin_group,
    rbac_add_user_to_group,
    rbac_admin_all_rights,
    rbac_create_admin_group,
    rbac_create_group,
    rbac_get_group_by_name,
    rbac_remove_user_from_group,
    rbac_user_allowed_for_model,
    rbac_user_blocked_for_model,
    rbac_user_has_role,
    rbac_user_has_role_exact,
    rbac_user_has_role_explain,
    rbac_user_is_admin_for_admin_group,
    rbac_user_is_group_admin,
    rbac_user_is_role_admin,
    role_to_parts,
)
from rbac.models import (
    RBACAdminGroupRole,
    RBACAdminTree,
    RBACModelDefault,
)
from tests.test_manager import CobaltTestManagerUnit

# App/model used for test defaults — unlikely to collide with real data
TEST_APP = "testrbac"
TEST_MODEL = "thing"


def _make_default(app, model, behaviour):
    """Create or update a RBACModelDefault for testing."""
    default, _ = RBACModelDefault.objects.update_or_create(
        app=app, model=model, defaults={"default_behaviour": behaviour}
    )
    return default


class RBACCoreTests:
    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        self.alan = manager.alan
        self.betty = manager.betty
        self.colin = manager.colin

    # ------------------------------------------------------------------ #
    # Utility functions
    # ------------------------------------------------------------------ #

    def test_01_role_to_parts_four_segment(self):
        result = role_to_parts("forums.forum.5.view")
        expected = ("forums", "forum", "5", "view")
        self.manager.save_results(
            status=result == expected,
            test_name="role_to_parts four-segment role",
            test_description="Splits 'app.model.id.action' into four parts",
            output=f"Got {result!r}, expected {expected!r}",
        )

    def test_02_role_to_parts_three_segment(self):
        result = role_to_parts("forums.forum.view")
        expected = ("forums", "forum", None, "view")
        self.manager.save_results(
            status=result == expected,
            test_name="role_to_parts three-segment role",
            test_description="Splits 'app.model.action' with model_instance=None",
            output=f"Got {result!r}, expected {expected!r}",
        )

    def test_03_allow_to_boolean_allow(self):
        result = allow_to_boolean("Allow")
        self.manager.save_results(
            status=result is True,
            test_name="allow_to_boolean Allow",
            test_description="'Allow' string returns True",
            output=f"Got {result!r}",
        )

    def test_04_allow_to_boolean_block(self):
        result = allow_to_boolean("Block")
        self.manager.save_results(
            status=result is False,
            test_name="allow_to_boolean Block",
            test_description="'Block' string returns False",
            output=f"Got {result!r}",
        )

    def test_05_allow_to_boolean_other(self):
        result = allow_to_boolean("anything")
        self.manager.save_results(
            status=result is False,
            test_name="allow_to_boolean other string",
            test_description="Any string other than 'Allow' returns False",
            output=f"Got {result!r}",
        )

    # ------------------------------------------------------------------ #
    # Group creation and lookup
    # ------------------------------------------------------------------ #

    def test_06_create_group(self):
        group = rbac_create_group("test.qual", "grp1", "Test group")
        self.manager.save_results(
            status=group is not None and group.name == "test.qual.grp1",
            test_name="rbac_create_group creates group",
            test_description="Creates a new RBACGroup with correct name",
            output=f"Group name: {group.name!r}",
        )

    def test_07_create_group_idempotent(self):
        group1 = rbac_create_group("test.qual", "grp_idem", "First")
        group2 = rbac_create_group("test.qual", "grp_idem", "Second")
        self.manager.save_results(
            status=group1.pk == group2.pk,
            test_name="rbac_create_group is idempotent",
            test_description="Calling create twice returns the same group",
            output=f"PKs: {group1.pk}, {group2.pk}",
        )

    def test_08_get_group_by_name_found(self):
        rbac_create_group("test.lookup", "findme", "desc")
        result = rbac_get_group_by_name("test.lookup.findme")
        self.manager.save_results(
            status=result is not False and result.name_item == "findme",
            test_name="rbac_get_group_by_name found",
            test_description="Returns group when it exists",
            output=f"Got {result!r}",
        )

    def test_09_get_group_by_name_missing(self):
        result = rbac_get_group_by_name("does.not.exist")
        self.manager.save_results(
            status=result is False,
            test_name="rbac_get_group_by_name missing",
            test_description="Returns False when group does not exist",
            output=f"Got {result!r}",
        )

    # ------------------------------------------------------------------ #
    # User ↔ group membership
    # ------------------------------------------------------------------ #

    def test_10_add_user_to_group(self):
        group = rbac_create_group("test.membership", "grp_add", "desc")
        user_group = rbac_add_user_to_group(self.alan, group)
        self.manager.save_results(
            status=user_group is not None and user_group.member == self.alan,
            test_name="rbac_add_user_to_group adds user",
            test_description="User is added to group and UserGroup is returned",
            output=f"UserGroup member: {user_group.member!r}",
        )

    def test_11_add_user_to_group_idempotent(self):
        group = rbac_create_group("test.membership", "grp_idem", "desc")
        ug1 = rbac_add_user_to_group(self.alan, group)
        ug2 = rbac_add_user_to_group(self.alan, group)
        self.manager.save_results(
            status=ug1.pk == ug2.pk,
            test_name="rbac_add_user_to_group is idempotent",
            test_description="Adding the same user twice returns the same record",
            output=f"PKs: {ug1.pk}, {ug2.pk}",
        )

    def test_12_remove_user_from_group(self):
        group = rbac_create_group("test.membership", "grp_rm", "desc")
        rbac_add_user_to_group(self.betty, group)
        result = rbac_remove_user_from_group(self.betty, group)
        # User should no longer be in group
        from rbac.models import RBACUserGroup

        still_in = RBACUserGroup.objects.filter(member=self.betty, group=group).exists()
        self.manager.save_results(
            status=result is True and not still_in,
            test_name="rbac_remove_user_from_group removes user",
            test_description="Returns True and user is no longer in group",
            output=f"return={result!r}, still_in={still_in}",
        )

    # ------------------------------------------------------------------ #
    # Role assignment
    # ------------------------------------------------------------------ #

    def test_13_add_role_to_group_allow(self):
        group = rbac_create_group("test.roles", "grp_allow", "desc")
        role = rbac_add_role_to_group(group, TEST_APP, TEST_MODEL, "view", "Allow")
        self.manager.save_results(
            status=role is not None and role.rule_type == "Allow",
            test_name="rbac_add_role_to_group Allow",
            test_description="Adds an Allow role to a group",
            output=f"rule_type={role.rule_type!r}",
        )

    def test_14_add_role_to_group_with_model_id(self):
        group = rbac_create_group("test.roles", "grp_model_id", "desc")
        role = rbac_add_role_to_group(
            group, TEST_APP, TEST_MODEL, "edit", "Allow", model_id=42
        )
        self.manager.save_results(
            status=role.model_id == 42,
            test_name="rbac_add_role_to_group with model_id",
            test_description="Adds a role with a specific model instance ID",
            output=f"model_id={role.model_id!r}",
        )

    def test_15_add_role_to_group_idempotent(self):
        group = rbac_create_group("test.roles", "grp_idem_role", "desc")
        r1 = rbac_add_role_to_group(group, TEST_APP, TEST_MODEL, "view", "Allow")
        r2 = rbac_add_role_to_group(group, TEST_APP, TEST_MODEL, "view", "Allow")
        self.manager.save_results(
            status=r1.pk == r2.pk,
            test_name="rbac_add_role_to_group is idempotent",
            test_description="Adding the same role twice returns the same record",
            output=f"PKs: {r1.pk}, {r2.pk}",
        )

    # ------------------------------------------------------------------ #
    # rbac_user_has_role_exact
    # ------------------------------------------------------------------ #

    def test_16_has_role_exact_allow(self):
        group = rbac_create_group("test.exact", "grp_exact_allow", "desc")
        rbac_add_user_to_group(self.alan, group)
        rbac_add_role_to_group(group, TEST_APP, TEST_MODEL, "view", "Allow")
        result = rbac_user_has_role_exact(self.alan, f"{TEST_APP}.{TEST_MODEL}.view")
        self.manager.save_results(
            status=result == "Allow",
            test_name="rbac_user_has_role_exact returns Allow",
            test_description="Returns 'Allow' when user has exact Allow role",
            output=f"Got {result!r}",
        )

    def test_17_has_role_exact_block(self):
        group = rbac_create_group("test.exact", "grp_exact_block", "desc")
        rbac_add_user_to_group(self.alan, group)
        rbac_add_role_to_group(group, TEST_APP, TEST_MODEL, "delete", "Block")
        result = rbac_user_has_role_exact(self.alan, f"{TEST_APP}.{TEST_MODEL}.delete")
        self.manager.save_results(
            status=result == "Block",
            test_name="rbac_user_has_role_exact returns Block",
            test_description="Returns 'Block' when user has exact Block role",
            output=f"Got {result!r}",
        )

    def test_18_has_role_exact_no_match(self):
        result = rbac_user_has_role_exact(self.betty, f"{TEST_APP}.{TEST_MODEL}.create")
        self.manager.save_results(
            status=result is None,
            test_name="rbac_user_has_role_exact no match",
            test_description="Returns None when user has no matching role",
            output=f"Got {result!r}",
        )

    def test_19_has_role_exact_wildcard_all(self):
        group = rbac_create_group("test.exact", "grp_all_action", "desc")
        rbac_add_user_to_group(self.alan, group)
        rbac_add_role_to_group(group, TEST_APP, TEST_MODEL, "all", "Allow", model_id=7)
        # Asking for .view should match the .all rule
        result = rbac_user_has_role_exact(self.alan, f"{TEST_APP}.{TEST_MODEL}.7.view")
        self.manager.save_results(
            status=result == "Allow",
            test_name="rbac_user_has_role_exact wildcard 'all' action",
            test_description="An 'all' action rule matches any specific action",
            output=f"Got {result!r}",
        )

    def test_20_has_role_exact_anonymous_user(self):
        from django.contrib.auth.models import AnonymousUser

        anon = AnonymousUser()
        result = rbac_user_has_role_exact(anon, f"{TEST_APP}.{TEST_MODEL}.view")
        self.manager.save_results(
            status=result is None,
            test_name="rbac_user_has_role_exact anonymous user",
            test_description="Anonymous users always return None (no access)",
            output=f"Got {result!r}",
        )

    # ------------------------------------------------------------------ #
    # rbac_user_has_role — full decision chain
    # ------------------------------------------------------------------ #

    def test_21_has_role_direct_allow(self):
        _make_default(TEST_APP, TEST_MODEL, "Block")
        group = rbac_create_group("test.chain", "grp_direct_allow", "desc")
        rbac_add_user_to_group(self.alan, group)
        rbac_add_role_to_group(group, TEST_APP, TEST_MODEL, "view", "Allow")
        result = rbac_user_has_role(self.alan, f"{TEST_APP}.{TEST_MODEL}.view")
        self.manager.save_results(
            status=result is True,
            test_name="rbac_user_has_role direct allow",
            test_description="Returns True when user has direct Allow rule",
            output=f"Got {result!r}",
        )

    def test_22_has_role_direct_block(self):
        _make_default(TEST_APP, TEST_MODEL, "Allow")
        group = rbac_create_group("test.chain", "grp_direct_block", "desc")
        rbac_add_user_to_group(self.betty, group)
        rbac_add_role_to_group(group, TEST_APP, TEST_MODEL, "edit", "Block")
        result = rbac_user_has_role(self.betty, f"{TEST_APP}.{TEST_MODEL}.edit")
        self.manager.save_results(
            status=result is False,
            test_name="rbac_user_has_role direct block",
            test_description="Returns False when user has direct Block rule",
            output=f"Got {result!r}",
        )

    def test_23_has_role_falls_through_to_default_allow(self):
        _make_default(TEST_APP, TEST_MODEL, "Allow")
        # colin has no rules — should fall through to default Allow
        result = rbac_user_has_role(self.colin, f"{TEST_APP}.{TEST_MODEL}.view")
        self.manager.save_results(
            status=result is True,
            test_name="rbac_user_has_role falls through to Allow default",
            test_description="No specific rule → uses RBACModelDefault Allow",
            output=f"Got {result!r}",
        )

    def test_24_has_role_falls_through_to_default_block(self):
        _make_default(TEST_APP, TEST_MODEL, "Block")
        # colin has no rules — should fall through to default Block
        result = rbac_user_has_role(self.colin, f"{TEST_APP}.{TEST_MODEL}.create")
        self.manager.save_results(
            status=result is False,
            test_name="rbac_user_has_role falls through to Block default",
            test_description="No specific rule → uses RBACModelDefault Block",
            output=f"Got {result!r}",
        )

    def test_25_has_role_higher_level_rule(self):
        """4-part role with no specific match should check 3-part higher-level rule."""
        _make_default(TEST_APP, TEST_MODEL, "Block")
        group = rbac_create_group("test.chain", "grp_higher", "desc")
        rbac_add_user_to_group(self.alan, group)
        # Give alan a generic 'view' right (no model_id)
        rbac_add_role_to_group(group, TEST_APP, TEST_MODEL, "view", "Allow")
        # Ask for a specific instance (4-part) — no exact match, but higher-level matches
        result = rbac_user_has_role(self.alan, f"{TEST_APP}.{TEST_MODEL}.99.view")
        self.manager.save_results(
            status=result is True,
            test_name="rbac_user_has_role higher-level rule fallback",
            test_description="4-part role with no match escalates to 3-part rule",
            output=f"Got {result!r}",
        )

    def test_26_has_role_no_default_raises(self):
        """TypeError is raised when no RBACModelDefault exists for app/model."""
        RBACModelDefault.objects.filter(app="orphan", model="orphan").delete()
        try:
            rbac_user_has_role(self.colin, "orphan.orphan.view")
            raised = False
        except TypeError:
            raised = True
        self.manager.save_results(
            status=raised,
            test_name="rbac_user_has_role raises TypeError for missing default",
            test_description="Raises TypeError when no default is configured",
            output=f"raised={raised}",
        )

    def test_27_has_role_explain_returns_string(self):
        _make_default(TEST_APP, TEST_MODEL, "Allow")
        result = rbac_user_has_role_explain(self.alan, f"{TEST_APP}.{TEST_MODEL}.view")
        self.manager.save_results(
            status=isinstance(result, str) and len(result) > 0,
            test_name="rbac_user_has_role_explain returns non-empty string",
            test_description="Explain function returns a non-empty diagnostic string",
            output=f"Type: {type(result).__name__}, length: {len(result)}",
        )

    # ------------------------------------------------------------------ #
    # rbac_user_blocked_for_model / rbac_user_allowed_for_model
    # ------------------------------------------------------------------ #

    def test_28_blocked_for_model_requires_allow_default(self):
        _make_default(TEST_APP, TEST_MODEL, "Block")
        try:
            rbac_user_blocked_for_model(self.alan, TEST_APP, TEST_MODEL, "view")
            raised = False
        except ReferenceError:
            raised = True
        self.manager.save_results(
            status=raised,
            test_name="rbac_user_blocked_for_model rejects Block default",
            test_description="ReferenceError when model default is Block",
            output=f"raised={raised}",
        )

    def test_29_blocked_for_model_user_allow_overrides_everyone_block(self):
        """User-specific Allow rule removes an ID from the blocked list."""
        _make_default(TEST_APP, TEST_MODEL, "Allow")
        from cobalt.settings import RBAC_EVERYONE
        from accounts.models import User as UserModel

        everyone = UserModel.objects.get(pk=RBAC_EVERYONE)
        # Block model_id=77 for everyone
        everyone_grp = rbac_create_group(
            "test.blocked", "grp_everyone_block_77", "desc"
        )
        rbac_add_user_to_group(everyone, everyone_grp)
        rbac_add_role_to_group(
            everyone_grp, TEST_APP, TEST_MODEL, "view", "Block", model_id=77
        )
        # Give the specific user an Allow override for model_id=77
        user_grp = rbac_create_group("test.blocked", "grp_user_allow_77", "desc")
        rbac_add_user_to_group(self.alan, user_grp)
        rbac_add_role_to_group(
            user_grp, TEST_APP, TEST_MODEL, "view", "Allow", model_id=77
        )
        result = rbac_user_blocked_for_model(self.alan, TEST_APP, TEST_MODEL, "view")
        self.manager.save_results(
            status=77 not in result,
            test_name="rbac_user_blocked_for_model user Allow overrides everyone Block",
            test_description="User-specific Allow for an ID removes it from the blocked list",
            output=f"Got {result!r}, 77 should be absent",
        )

    def test_30_blocked_for_model_returns_blocked_ids(self):
        _make_default(TEST_APP, TEST_MODEL, "Allow")
        from cobalt.settings import RBAC_EVERYONE
        from accounts.models import User as UserModel

        everyone = UserModel.objects.get(pk=RBAC_EVERYONE)
        grp = rbac_create_group("test.blocked", "grp_blocked_ids", "desc")
        rbac_add_user_to_group(everyone, grp)
        rbac_add_role_to_group(grp, TEST_APP, TEST_MODEL, "view", "Block", model_id=55)
        result = rbac_user_blocked_for_model(self.alan, TEST_APP, TEST_MODEL, "view")
        self.manager.save_results(
            status=55 in result,
            test_name="rbac_user_blocked_for_model includes everyone-blocked ids",
            test_description="IDs blocked for Everyone appear in the blocked list",
            output=f"Got {result!r}",
        )

    def test_31_allowed_for_model_requires_block_default(self):
        _make_default(TEST_APP, TEST_MODEL, "Allow")
        try:
            rbac_user_allowed_for_model(self.alan, TEST_APP, TEST_MODEL, "view")
            raised = False
        except ReferenceError:
            raised = True
        self.manager.save_results(
            status=raised,
            test_name="rbac_user_allowed_for_model rejects Allow default",
            test_description="ReferenceError when model default is Allow",
            output=f"raised={raised}",
        )

    def test_32_allowed_for_model_user_allowed_all(self):
        """User with a generic (no model_id) Allow rule gets ('True', [])."""
        _make_default(TEST_APP, TEST_MODEL, "Block")
        grp = rbac_create_group("test.allowed", "grp_all_allowed", "desc")
        rbac_add_user_to_group(self.alan, grp)
        rbac_add_role_to_group(grp, TEST_APP, TEST_MODEL, "view", "Allow")
        allowed, ids = rbac_user_allowed_for_model(
            self.alan, TEST_APP, TEST_MODEL, "view"
        )
        self.manager.save_results(
            status=allowed == "True" and ids == [],
            test_name="rbac_user_allowed_for_model all-access",
            test_description="User with generic Allow rule returns ('True', [])",
            output=f"Got ({allowed!r}, {ids!r})",
        )

    def test_33_allowed_for_model_specific_ids(self):
        """User allowed for specific model_ids via Everyone."""
        _make_default(TEST_APP, TEST_MODEL, "Block")
        from cobalt.settings import RBAC_EVERYONE
        from accounts.models import User as UserModel

        everyone = UserModel.objects.get(pk=RBAC_EVERYONE)
        grp = rbac_create_group("test.allowed", "grp_specific_ids", "desc")
        rbac_add_user_to_group(everyone, grp)
        rbac_add_role_to_group(grp, TEST_APP, TEST_MODEL, "view", "Allow", model_id=10)
        rbac_add_role_to_group(grp, TEST_APP, TEST_MODEL, "view", "Allow", model_id=20)
        allowed, ids = rbac_user_allowed_for_model(
            self.colin, TEST_APP, TEST_MODEL, "view"
        )
        self.manager.save_results(
            status=allowed is False and 10 in ids and 20 in ids,
            test_name="rbac_user_allowed_for_model specific id list",
            test_description="Returns allowed id list when specific Allow rules exist",
            output=f"Got ({allowed!r}, {ids!r})",
        )

    # ------------------------------------------------------------------ #
    # Admin functions
    # ------------------------------------------------------------------ #

    def test_34_admin_all_rights_empty(self):
        result = rbac_admin_all_rights(self.colin)
        self.manager.save_results(
            status=isinstance(result, list),
            test_name="rbac_admin_all_rights returns list",
            test_description="Returns a list (possibly empty) of admin rights",
            output=f"Got {result!r}",
        )

    def test_35_admin_all_rights_with_role(self):
        admin_grp = rbac_create_admin_group("test.admin", "admin_rights_grp", "desc")
        rbac_add_user_to_admin_group(self.alan, admin_grp)
        RBACAdminGroupRole.objects.create(
            group=admin_grp, app="forums", model="forum", model_id=None
        )
        result = rbac_admin_all_rights(self.alan)
        self.manager.save_results(
            status="forums.forum" in result,
            test_name="rbac_admin_all_rights includes assigned role",
            test_description="Returns app.model string for admin group roles",
            output=f"Got {result!r}",
        )

    def test_36_user_is_group_admin_true(self):
        group = rbac_create_group("test.gadmin", "target_grp", "desc")
        admin_grp = rbac_create_admin_group("test.gadmin", "gadmin_grp", "desc")
        rbac_add_user_to_admin_group(self.alan, admin_grp)
        RBACAdminTree.objects.create(group=admin_grp, tree="test.gadmin.target_grp")
        result = rbac_user_is_group_admin(self.alan, group)
        self.manager.save_results(
            status=result is True,
            test_name="rbac_user_is_group_admin True",
            test_description="Returns True when admin tree covers the group",
            output=f"Got {result!r}",
        )

    def test_37_user_is_group_admin_prefix_match(self):
        group = rbac_create_group("test.gadmin.sub", "sub_grp", "desc")
        admin_grp = rbac_create_admin_group("test.gadmin", "gadmin_prefix", "desc")
        rbac_add_user_to_admin_group(self.alan, admin_grp)
        # Tree prefix "test.gadmin." should match group "test.gadmin.sub.sub_grp"
        RBACAdminTree.objects.create(group=admin_grp, tree="test.gadmin")
        result = rbac_user_is_group_admin(self.alan, group)
        self.manager.save_results(
            status=result is True,
            test_name="rbac_user_is_group_admin prefix match",
            test_description="Partial tree path prefix also grants group admin",
            output=f"Got {result!r}",
        )

    def test_38_user_is_group_admin_false(self):
        group = rbac_create_group("test.gadmin", "other_grp", "desc")
        result = rbac_user_is_group_admin(self.betty, group)
        self.manager.save_results(
            status=result is False,
            test_name="rbac_user_is_group_admin False",
            test_description="Returns False when user has no admin tree entry",
            output=f"Got {result!r}",
        )

    def test_39_user_is_role_admin_exact(self):
        admin_grp = rbac_create_admin_group("test.radmin", "radmin_exact", "desc")
        rbac_add_user_to_admin_group(self.alan, admin_grp)
        RBACAdminGroupRole.objects.create(
            group=admin_grp, app="forums", model="forum", model_id=3
        )
        result = rbac_user_is_role_admin(self.alan, "forums.forum.3")
        self.manager.save_results(
            status=result is True,
            test_name="rbac_user_is_role_admin exact match",
            test_description="Returns True for exact app.model.id role admin match",
            output=f"Got {result!r}",
        )

    def test_40_user_is_role_admin_generic(self):
        """app.model.id admin role should also be granted by generic app.model."""
        admin_grp = rbac_create_admin_group("test.radmin", "radmin_generic", "desc")
        rbac_add_user_to_admin_group(self.alan, admin_grp)
        RBACAdminGroupRole.objects.create(
            group=admin_grp, app="events", model="org", model_id=None
        )
        result = rbac_user_is_role_admin(self.alan, "events.org.7")
        self.manager.save_results(
            status=result is True,
            test_name="rbac_user_is_role_admin generic fallback",
            test_description="Generic app.model admin grants admin for app.model.id",
            output=f"Got {result!r}",
        )

    def test_41_user_is_role_admin_false(self):
        # Use TEST_APP/TEST_MODEL to avoid collisions with pre-existing test DB admin data
        result = rbac_user_is_role_admin(self.betty, f"{TEST_APP}.{TEST_MODEL}.99")
        self.manager.save_results(
            status=result is False,
            test_name="rbac_user_is_role_admin False",
            test_description="Returns False when user has no matching admin role",
            output=f"Got {result!r}",
        )

    def test_42_user_is_admin_for_admin_group_true(self):
        admin_grp = rbac_create_admin_group("test.aag", "aag_true", "desc")
        rbac_add_user_to_admin_group(self.alan, admin_grp)
        result = rbac_user_is_admin_for_admin_group(self.alan, admin_grp)
        self.manager.save_results(
            status=result is True,
            test_name="rbac_user_is_admin_for_admin_group True",
            test_description="Returns True when user is a member of the admin group",
            output=f"Got {result!r}",
        )

    def test_43_user_is_admin_for_admin_group_false(self):
        admin_grp = rbac_create_admin_group("test.aag", "aag_false", "desc")
        result = rbac_user_is_admin_for_admin_group(self.betty, admin_grp)
        self.manager.save_results(
            status=result is False,
            test_name="rbac_user_is_admin_for_admin_group False",
            test_description="Returns False when user is not a member of the admin group",
            output=f"Got {result!r}",
        )
