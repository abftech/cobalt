"""Role Based Access Control Core

This handles the core functions for role based security for Cobalt.

See `RBAC Overview`_ for more details.

.. _RBAC Overview:
   ./rbac_overview.html
"""

from django.db.models import Q

from .models import (
    RBACGroup,
    RBACUserGroup,
    RBACGroupRole,
    RBACAdminUserGroup,
    RBACAdminGroupRole,
    RBACModelDefault,
    RBACAdminTree,
    RBACAdminGroup,
)
from cobalt.settings import RBAC_EVERYONE
from accounts.models import User
from organisations.models import Organisation


def rbac_create_group(name_qualifier, name_item, description):
    """Create an RBAC group

    Args:
        name_qualifier(str): where in the tree the group will go
        name_item(str): name
        description(str): free format description

    Returns:
        RBACGroup
    """

    group = RBACGroup.objects.filter(
        name_qualifier=name_qualifier, name_item=name_item
    ).first()
    if not group:
        group = RBACGroup(
            name_qualifier=name_qualifier, name_item=name_item, description=description
        )
        group.save()
    return group


def rbac_create_admin_group(name_qualifier, name_item, description):
    """create an admin group
    Args:
         name_qualifier(str): where in the tree the group will go
         name_item(str): name
         description(str): free format description

     Returns:
         RBACAdminGroup
    """

    group = RBACAdminGroup.objects.filter(
        name_qualifier=name_qualifier, name_item=name_item
    ).first()
    if not group:
        group = RBACAdminGroup(
            name_qualifier=name_qualifier, name_item=name_item, description=description
        )
        group.save()
    return group


def rbac_delete_group(group):
    """Delete an RBAC group. Cascade takes care of related objects.

    Args:
        group(RBACGroup): Group to delete

    Returns:
        bool
    """

    try:
        group.delete()
        return True
    except RBACGroup.DoesNotExist:
        return False


def rbac_get_group_by_name(group_name):
    """Get an RBAC group by name

    Args:
        group_name(str): group name to find

    Returns:
        RBACGroup
    """

    name_parts = group_name.split(".")
    group_name_item = name_parts[-1]
    group_name_qualifier = ".".join(name_parts[:-1])

    try:
        return RBACGroup.objects.get(
            name_qualifier=group_name_qualifier, name_item=group_name_item
        )
    except RBACGroup.DoesNotExist:
        return False


def rbac_get_admin_group_by_name(group_name):
    """Get an RBAC Admin group by name

    Args:
        group_name(str): group name to find

    Returns:
        RBACGroup
    """

    name_parts = group_name.split(".")
    group_name_item = name_parts[-1]
    group_name_qualifier = ".".join(name_parts[:-1])

    try:
        return RBACAdminGroup.objects.get(
            name_qualifier=group_name_qualifier, name_item=group_name_item
        )
    except RBACAdminGroup.DoesNotExist:
        return False


def rbac_delete_group_by_name(group_name):
    """Delete an RBAC group by name

    Args:
        group_name(str): group name to delete

    Returns:
        bool
    """

    rbac_get_group_by_name(group_name).delete()


def rbac_delete_admin_group_by_name(group_name):
    """Delete an RBAC Admin group by name

    Args:
        group_name(str): group name to delete

    Returns:
        bool
    """

    rbac_get_admin_group_by_name(group_name).delete()


def rbac_add_user_to_group(member: User, group: RBACGroup) -> RBACGroup:
    """Adds a user to an RBAC group

    Args:
        member(User): standard user object
        group(RBACGroup): group to add to

    Returns:
        RBACUserGroup
    """

    user_group = RBACUserGroup.objects.filter(member=member, group=group).first()
    if not user_group:
        user_group = RBACUserGroup(member=member, group=group)
        user_group.save()
    return user_group


def rbac_add_user_to_admin_group(member, admin_group):
    """Adds a user to an RBAC admin group

    Args:
        member(User): standard user object
        group(RBACAdminGroup): group to add to

    Returns:
        Nothing
    """

    if not RBACAdminUserGroup.objects.filter(group=admin_group, member=member).exists():
        RBACAdminUserGroup(group=admin_group, member=member).save()


def rbac_remove_user_from_group(member, group):
    """Removes a user from an RBAC group

    Args:
        member(User): standard user object
        group(RBACGroup): group to remove user from

    Returns:
        bool
    """

    try:
        user_group = RBACUserGroup.objects.filter(member=member, group=group)
        user_group.delete()
        return True
    except RBACUserGroup.DoesNotExist:
        return False


def rbac_remove_admin_user_from_group(member, group):
    """Removes a user from an RBAC admin group

    Args:
        member(User): standard user object
        group(RBACAdminGroup): group to remove user from

    Returns:
        bool
    """

    try:
        user_group = RBACAdminUserGroup.objects.filter(member=member, group=group)
        user_group.delete()
        return True
    except RBACAdminUserGroup.DoesNotExist:
        return False


def rbac_add_role_to_group(group, app, model, action, rule_type, model_id=None):
    """Adds a role to an RBAC group

    Args:
        group(RBACGroup): group
        app(str):   name of the app
        model(str): name of the model
        action(str):    action
        rule_type(str): Allow or Block
        model_id(int):  model instance (Optional)

    Returns:
        RBACGroupRole
    """

    group_role = RBACGroupRole.objects.filter(
        group=group,
        app=app,
        model=model,
        model_id=model_id,
        action=action,
        rule_type=rule_type,
    ).first()

    if not group_role:
        group_role = RBACGroupRole()
        group_role.group = group
        group_role.app = app
        group_role.model = model
        group_role.action = action
        group_role.rule_type = rule_type
        group_role.model_id = model_id
        group_role.save()

    return group_role


def rbac_user_has_role_exact(member, role):
    """check if a user has an exact role

    This is called by rbac_user_has_role to check exact roles. The process
    for checking an exact role is always the same. rbac_user_has_role has
    the logic to put this together at a higher level and to use defaults
    in order to work out if the combination of rules allows a user to do
    something. This function only checks at the most specific level.

    Args:
        member(User): standard user object
        role(str): role to check

    Returns:
        string: "Allow", "Block", or None for no match
    """

    # If user isn't logged in, they have no access
    if member.is_anonymous:
        return

    (app, model, model_instance, action) = role_to_parts(role)
    # we also match against an action of all. e.g. if the role is:
    #  forums.forum.5.create then we will also accept finding:
    #  forums.forum.5.all.
    if model_instance:
        all_role = "%s.%s.%s.all" % (app, model, model_instance)
    else:
        all_role = "%s.%s.all" % (app, model)

    groups = RBACUserGroup.objects.filter(member=member).values_list("group")
    matches = RBACGroupRole.objects.filter(group__in=groups)

    for m in matches:
        if m.role == role or m.role == all_role:
            return m.rule_type

    # no match
    return None


def rbac_user_has_role_exact_explain(member, role):
    """check if a user has an exact role and explain why

    Args:
        member(User): standard user object
        role(str): role to check

    Returns:
        string: "Allow", "Block", or None for no match
        string: Role that matched
        group: The group that matched
    """
    (app, model, model_instance, action) = role_to_parts(role)
    # we also match against an action of all. e.g. if the role is:
    #  forums.forum.5.create then we will also accept finding:
    #  forums.forum.5.all.
    if model_instance:
        all_role = "%s.%s.%s.all" % (app, model, model_instance)
    else:
        all_role = "%s.%s.all" % (app, model)

    groups = RBACUserGroup.objects.filter(member=member).values_list("group")
    matches = RBACGroupRole.objects.filter(group__in=groups)

    for m in matches:
        if m.role == role:
            return m.rule_type, m, m.group

        if m.role == all_role:
            return m.rule_type, m, m.group

    # no match
    return (None, None, None)


def rbac_user_has_role(member, role, debug=False):
    """check if a user has a specific role

    Args:
        member(User): standard user object
        role(str): role to check
        debug(bool): print debug info

    Returns:
        bool: True or False for user role
    """

    # Is there a specific rule for this user and role
    return_code = rbac_user_has_role_exact(member, role)

    if return_code:
        return allow_to_boolean(return_code)

    # Is there a specific rule for Everyone and this role
    everyone = User.objects.get(pk=RBAC_EVERYONE)

    return_code = rbac_user_has_role_exact(everyone, role)

    if return_code:
        return allow_to_boolean(return_code)

    # Is there a higher role. eg. for forums.forum.5 if no match then is there
    # a rule for forums.forum. We only go one level up for performance reasons.
    if role.count(".") == 3:  # 3 levels plus action
        parts = role.split(".")
        role = "%s.%s.%s" % (parts[0], parts[1], parts[3])  # f.f.5.create -> f.f.create

        # next level rule for this user
        return_code = rbac_user_has_role_exact(member, role)

        if return_code:
            return allow_to_boolean(return_code)

        #  next level rule for everyone
        return_code = rbac_user_has_role_exact(everyone, role)

        if return_code:
            return allow_to_boolean(return_code)

    # No match or no higher rule - use default
    (app, model, model_instance, action) = role_to_parts(role)
    try:
        default = (
            RBACModelDefault.objects.filter(app=app, model=model)
            .values_list("default_behaviour")
            .first()[0]
        )
    except TypeError:
        raise TypeError(
            "It looks like there is no default set up for app=%s model=%s"
            % (app, model)
        )
    return allow_to_boolean(default)


def rbac_user_has_role_explain(member, role):
    """check if a user has a specific role and explains why

    Args:
        member(User): standard user object
        role(str): role to check

    Returns:
        bool: True or False for user role
    """

    log = f"Checking Member: {member} Role: {role}\n\n"

    # Is there a specific rule for this user and role
    (return_code, role_match, group) = rbac_user_has_role_exact_explain(member, role)
    if return_code:
        log += "There is a specific rule for this user\n"
        log += "GroupRole: [id=%s] %s %s\n" % (
            role_match.id,
            role_match.role,
            role_match.rule_type,
        )
        log += "Group: [%s] %s\n" % (group.id, group)
        ret = f"{return_code}\n\n{log}"
        return ret

    log += "No specific rule for user\n"

    # Is there a specific rule for Everyone and this role
    everyone = User.objects.get(pk=RBAC_EVERYONE)
    (return_code, role_match, group) = rbac_user_has_role_exact_explain(everyone, role)
    if return_code:
        log += "There is a specific rule for EVERYONE\n"
        log += "GroupRole: [id=%s] %s %s\n" % (
            role_match.id,
            role_match.role,
            role_match.rule_type,
        )
        log += "Group: [%s] %s\n" % (group.id, group)
        ret = f"{return_code}\n\n{log}"
        return ret

    log += "No specific rule for EVERYONE\n"

    # Is there a higher role. eg. for forums.forum.5 if no match then is there
    # a rule for forums.forum. We only go one level up for performance reasons.
    if role.count(".") == 3:  # 3 levels plus action
        parts = role.split(".")
        role = "%s.%s.%s" % (parts[0], parts[1], parts[3])  # f.f.5.create -> f.f.create

        # next level rule for this user

        (return_code, role_match, group) = rbac_user_has_role_exact_explain(
            member, role
        )
        if return_code:
            log += "There is a higher level rule for this user\n"
            log += "GroupRole: [id=%s] %s %s\n" % (
                role_match.id,
                role_match.role,
                role_match.rule_type,
            )
            log += "Group: [%s] %s\n" % (group.id, group)
            ret = f"{return_code}\n\n{log}"
            return ret

        log += "No higher level rule for this user\n"

        #  next level rule for everyone
        (return_code, role_match, group) = rbac_user_has_role_exact_explain(
            everyone, role
        )
        if return_code:
            log += "There is a higher level rule for EVERYONE\n"
            log += "GroupRole: [id=%s] %s %s\n" % (
                role_match.id,
                role_match.role,
                role_match.rule_type,
            )
            log += "Group: [%s] %s\n" % (group.id, group)
            ret = f"{return_code}\n\n{log}"
            return ret

        log += "No higher level rule for EVERYONE\n"

    # No match or no higher rule - use default
    (app, model, model_instance, action) = role_to_parts(role)
    try:
        default = (
            RBACModelDefault.objects.filter(app=app, model=model)
            .values_list("default_behaviour")
            .first()[0]
        )
    except TypeError:
        raise TypeError(
            "It looks like there is no default set up for app=%s model=%s"
            % (app, model)
        )
    log += "Using default: %s" % default
    ret = f"{default}\n\n{log}"
    return ret


def allow_to_boolean(test_string):
    """takes a string and returns True if it is "Allow" """

    return test_string == "Allow"


def role_to_parts(role):
    """take a role string and return it in parts

    Args:
        role(str): string in format e.g. forums.forum.5.view

    Returns:
        tuple: (app, model, model_instance, action)
    """

    parts = role.split(".")
    app = parts[0]
    model = parts[1]
    action = parts[-1]

    model_instance = parts[2] if len(parts) == 4 else None
    return app, model, model_instance, action


def rbac_user_blocked_for_model(user, app, model, action):
    """returns a list of model instances which the user cannot view

    Args:
        user(User): standard user object
        app(str):   application name
        model(str): model name
        action(str):    action required

    Returns:
        list:   list of model_instances explicitly block
    """

    default = RBACModelDefault.objects.filter(app=app, model=model).first()

    if not default:
        raise ReferenceError("%s.%s not set up in RBACModelDefault" % (app, model))

    if default.default_behaviour == "Block":
        raise ReferenceError("Only supported for default Allow models")

    # get block rules first for both this user and everyone
    groups = RBACUserGroup.objects.filter(
        member__in=[user.id, RBAC_EVERYONE]
    ).values_list("group")

    everyone_matches = RBACGroupRole.objects.filter(
        group__in=groups, rule_type="Block", action__in=[action, "all"]
    ).values_list("model_id")

    # get rules for this user that allow
    user_groups = RBACUserGroup.objects.filter(member=user).values_list("group")

    user_matches = RBACGroupRole.objects.filter(
        group__in=user_groups, rule_type="Allow", action__in=[action, "all"]
    ).values_list("model_id")

    # allow rules for this user override block rules for everyone
    ret = []
    for m in everyone_matches:
        if m not in user_matches:
            ret.append(m[0])
    return ret


def rbac_user_allowed_for_model(user, app, model, action):
    """returns a tuple.

    Args:
        user(User): standard user object
        app(str):   application name
        model(str): model name
        action(str):    action required

    Returns:
        tuple:  boolean - allowed for all, list - list of model_instances explicitly allowed
    """

    default = RBACModelDefault.objects.filter(app=app, model=model).first()

    if not default:
        raise ReferenceError("%s.%s not set up in RBACModelDefault" % (app, model))

    if default.default_behaviour == "Allow":
        raise ReferenceError("Only supported for default Block models")

    # See if user has everything and return now if true
    if rbac_user_has_role(user, "%s.%s.%s" % (app, model, action)):
        return ("True", [])

    # get all rules first for both this user and everyone
    groups = RBACUserGroup.objects.filter(
        member__in=[user.id, RBAC_EVERYONE]
    ).values_list("group")

    everyone_matches = RBACGroupRole.objects.filter(
        group__in=groups, rule_type="Allow", action__in=[action, "all"]
    ).values_list("model_id")

    everyone_matches = [em[0] for em in everyone_matches]  # strip tuple noise

    # get rules for this user that block
    user_groups = RBACUserGroup.objects.filter(member=user).values_list("group")

    user_matches = RBACGroupRole.objects.filter(
        group__in=user_groups, rule_type="Block", action__in=[action, "all"]
    ).values_list("model_id")

    user_matches = [um[0] for um in user_matches]  # strip tuple noise

    # allow rules for this user override block rules for everyone
    ret = [m for m in everyone_matches if m and m not in user_matches]
    return False, ret


def rbac_admin_all_rights(user):
    """returns a list of which apps, models and model_ids a user is an admin for

    Args:
        user(User): standard user object

    Returns:
        list:   list of App, model, model_id
    """

    groups = (
        RBACAdminUserGroup.objects.filter(member=user).values_list("group").distinct()
    )

    matches = RBACAdminGroupRole.objects.filter(group__in=groups).distinct()

    ret = []
    for m in matches:
        if m.model_id:
            ret_str = "%s.%s.%s" % (m.app, m.model, m.model_id)
        else:
            ret_str = "%s.%s" % (m.app, m.model)
        if ret_str not in ret:
            ret.append(ret_str)

    # Sort and strip any unnecessary e.g. if org.orgs is in here we don't need org.orgs.4
    pretty = []
    for item in ret:
        if item.count(".") == 2:
            higher = ".".join(item.split(".")[2])
            if higher not in ret:
                pretty.append(item)
        else:
            pretty.append(item)

    pretty.sort()

    return pretty


def rbac_user_is_group_admin(member, group):
    """check if a user has admin rights to a group based upon their rights
    in the tree. Note - they also need admin rights to the objects if they are
    intending to change the group. This only checks for the ability to change
    group membership or delete the group.

    Args:
        member(User): standard user object
        group(RBACGroup): group to check

    Returns:
        bool: True of False for user role
    """

    path = group.name

    group_list = RBACAdminUserGroup.objects.filter(member=member).values_list("group")

    trees = RBACAdminTree.objects.filter(group__in=group_list)

    for tree in trees:
        if tree.tree == path:
            return True
        # check for match on aaaaa.bbbbb.
        partial = tree.tree + "."
        if path.find(partial) == 0:
            return True

    return False


def rbac_user_is_role_admin(member, role):
    """check if a user is an admin for a specific role

    Args:
        member(User): standard user object
        role(str): role to check. should be from role.path e.g. forums.forum.3. No action in string.

    Returns:
        bool: True of False for user role
    """

    groups = RBACAdminUserGroup.objects.filter(member=member).values_list("group")
    matches = RBACAdminGroupRole.objects.filter(group__in=groups)

    # look for specific rule
    for m in matches:
        # compare strings not objects
        role_str = "%s" % role
        if m.model_id:
            m_str = "%s.%s.%s" % (m.app, m.model, m.model_id)
        else:
            m_str = "%s.%s" % (m.app, m.model)
        if m_str == role_str:
            return True

    # change role org.org.15 --> org.org
    parts = role.split(".")
    if len(parts) == 3:
        role = ".".join(parts[:-1])

        # look for general rule
        for m in matches:
            # compare strings not objects
            role_str = "%s" % role
            m_str = "%s.%s" % (m.app, m.model)

            if m_str == role_str:
                return True
    # No match
    return False


def rbac_user_is_admin_for_admin_group(member, group):
    """check if a user is an admin for an admin group. Any member of an
    admin group is automatically an administrator for that group.

    Args:
        member(User): standard user object
        group(RBACAdminGroup): admin group to check

    Returns:
        bool: True of False for user role
    """

    users = RBACAdminUserGroup.objects.filter(group=group)
    user_list = users.values_list("member", flat=True)
    if member.id in user_list:
        return True
    else:
        return False


def rbac_access_in_english(user):
    """returns what access a user has in plain English

    Args:
        user(User): a standard User object

    Returns:
        list: list of strings with user access explained
    """

    return rbac_access_in_english_sub(
        RBAC_EVERYONE, "Everyone"
    ) + rbac_access_in_english_sub(user, user.first_name)


def rbac_access_in_english_sub(user, this_name):
    """returns what access a user has in plain English

    Args:
        this_name(str): Will be Everyone or the user's first name
        user(User): a standard User object

    Returns:
        list: list of tuples - role, strings with user access explained
    """

    groups = RBACUserGroup.objects.filter(member=user).values_list("group")
    roles = RBACGroupRole.objects.filter(group__in=groups).order_by("app", "model")
    english = []
    for role in roles:

        # Generic messages first

        if role.rule_type == "Allow":
            verb = "can"
        else:
            verb = "cannot"

        if role.action == "all":
            action_word = "do everything"
        else:
            action_word = role.action

        if role.model_id:
            desc = f"{this_name} {verb} {action_word} in {role.model} no. {role.model_id} in the application '{role.app}'."
        else:
            desc = f"{this_name} {verb} {action_word} in every {role.model} in the application '{role.app}'."

        # some specific hard coding
        if role.app == "payments":
            if role.model == "global":
                if role.action in ["all", "edit"]:
                    desc = f"{this_name} is a global admin for the Payments module."
                elif role.action == "view":
                    desc = (
                        f"{this_name} has global view access for the Payments module."
                    )

            if role.model == "manage":
                # normal users have model_ids
                if role.model_id:
                    org = Organisation.objects.get(pk=role.model_id)
                    if role.action in ["all", "edit"]:
                        desc = f"{this_name} {verb} manage payments for {org}"
                    elif role.action == "view":
                        desc = f"{this_name} {verb} view payments for {org}"

                elif role.action in ["all", "edit"]:
                    desc = f"{this_name} {verb} manage payments for any organisation"
                elif role.action == "view":
                    desc = f"{this_name} {verb} view payments for any organisation"

        if (
            role.app == "support"
            and role.model == "helpdesk"
            and role.action in ["all", "edit"]
        ):
            desc = f"{this_name} {verb} use the Helpdesk module"

        if (
            role.app == "system"
            and role.model == "admin"
            and role.action in ["all", "edit"]
        ):
            desc = f"{this_name} {verb} manage global system settings"

        if role.app == "events":
            if role.model == "org":
                # normal users have model_ids
                if role.model_id:
                    org = Organisation.objects.get(pk=role.model_id)
                    if org:
                        desc = f"{this_name} {verb} create and run congresses for {org}"
                    else:
                        desc = f"{this_name} {verb} create and run congresses for org_id={role.model_id} (org not found)."
                else:
                    desc = f"{this_name} {verb} create and run congresses for all organisations."
            if role.model == "global":
                desc = f"{this_name} {verb} manage global settings for Events such as creating new types of congress."

        if role.app == "club_sessions" and role.model == "sessions":

            # Normal users have a model_id
            if role.model_id:
                org = Organisation.objects.get(pk=role.model_id)
                if role.action in ["edit", "all"]:
                    desc = f"{this_name} can run sessions for {org}"
                elif role.action == "view":
                    desc = f"{this_name} can view sessions for {org}"

            # admin user don't have a model_id
            elif role.action in ["edit", "all"]:
                desc = f"{this_name} can run sessions for any club"
            elif role.action == "view":
                desc = f"{this_name} can view sessions for any club"

        if role.app == "notifications":
            if role.model == "admin" and role.action in ["all", "view"]:
                desc = f"{this_name} is a global administrator for the Notifications module"

            if role.model == "orgcomms":
                # normal users have a model_id
                if role.model_id:
                    org = Organisation.objects.get(pk=role.model_id)
                    if role.action in ["all", "edit"]:
                        desc = f"{this_name} can administer comms for {org}"

                elif role.action in ["all", "edit"]:
                    desc = f"{this_name} can administer comms for all organisations"

            if role.model == "realtime_send":
                desc = f"{this_name} can send real time messages to members such as SMS"

        if role.app == "orgs":
            if role.model == "admin":
                desc = f"{this_name} is a global admin for Orgs. They can add or delete clubs etc."

            if role.model == "members":
                # normal users have a model_id
                if role.model_id:
                    org = Organisation.objects.get(pk=role.model_id)
                    if role.action in ["edit", "all"]:
                        desc = f"{this_name} can add, remove and edit members for {org}"

                elif role.action in ["edit", "all"]:
                    desc = f"{this_name} can add, remove and edit members for any organisation"

            if role.model == "org":
                # normal users have a model_id
                if role.model_id:
                    org = Organisation.objects.get(pk=role.model_id)
                    if role.action in ["edit", "all"]:
                        desc = f"{this_name} can edit details for {org} such as address and name"
                    elif role.action == "view":
                        desc = f"{this_name} can access the club menu for {org}"

                elif role.action in ["edit", "all"]:
                    desc = f"{this_name} can edit details for any organisation"

            if role.model == "state":
                # normal users have a model_id
                if role.model_id:
                    state = Organisation.objects.get(pk=role.model_id)
                    if role.action in ["edit", "all"]:
                        desc = f"{this_name} add clubs etc for state: {state}"

        # Add to list
        english.append((role, desc))

    return english


def rbac_get_admins_for_group(group):
    """returns a queryset of admins who can change users for a given group"""

    path = group.name
    # Get the groups who have access to this part of the tree
    # if path is rbac.abf.forums we also want to match on rbac.abf or rbac
    # this needs a SQL query like WHERE 'rbac.abf.forums' like tree||'%'
    # Django can't do this so we need to use extra to add out own SQL
    tree = RBACAdminTree.objects.extra(where=["%s LIKE tree||'%%'"], params=[path])
    tree_groups = tree.values("group")
    # Get the members of the groups
    admins = RBACAdminUserGroup.objects.filter(group__in=tree_groups).distinct("member")
    return admins


def rbac_add_role_to_admin_group(group, app, model, model_id=None):
    """adds a role to an admin group"""

    if not RBACAdminGroupRole.objects.filter(
        group=group, app=app, model=model, model_id=model_id
    ).exists():
        item = RBACAdminGroupRole(group=group, app=app, model=model, model_id=model_id)
        item.save()


def rbac_user_role_list(user, app, model):
    """return list of roles a user has for part of the tree.

    This takes in a user and and app/model combination and returns the list of
    model_ids and actions that a user can perform. For example, if you provide::

        app = "forums"
        model = "forum"

    This could return::

        [(23, "edit"), (23, "delete"), (55, "edit")]

    Only returns things with "Allow" so only works for Block default models.
    """

    groups = RBACUserGroup.objects.filter(member=user).values_list("group")
    matches = RBACGroupRole.objects.filter(
        group__in=groups, app=app, model=model, rule_type="Allow"
    )

    ret = []
    for match in matches:
        item = (match.model_id, match.action)
        ret.append(item)

    return ret


def rbac_get_groups_for_role(role):
    """takes a role and lists the groups that can provide it.

    Only works for allow rules with model ids"""

    (app, model, model_instance, action) = role_to_parts(role)

    return RBACGroupRole.objects.filter(
        app=app, model=model, model_id=model_instance
    ).filter(Q(action=action) | Q(action="All"))


def rbac_get_roles_for_group(group):
    """list roles that are provided by a group.

    e.g. if group 17 has RBACGroupRoles:
        app.model.model_id.action
        org.pencil.12.edit
        payments.chair.12.view

        This will return:
        [
        {'app': 'org', 'model': 'pencil', 'action': 'edit'},
        {'app': 'payments', 'model': 'chair', 'action': 'view'}
        ]

    Args:
        group(RBACGroup): group to check

    Returns:
       queryset dictionary: app, model, action

    """

    return RBACGroupRole.objects.filter(group=group).values("app", "model", "action")


def rbac_get_users_in_group_by_name(group_name):
    """returns a list of users in a group using the group name

    Args:
        group_name(str): group name to check

    Returns:
        list: List of users

    """

    group = rbac_get_group_by_name(group_name)
    return rbac_get_users_in_group(group)


def rbac_get_users_in_group(group):
    """returns a list of users in a group

    Args:
        group(RBACGroup): group to check

    Returns:
        list: List of users

    """

    return User.objects.filter(rbacusergroup__group=group).order_by("first_name")


def rbac_get_admin_users_in_group(admin_group):
    """returns a list of users in an admin group

    Args:
        admin_group(RBACAdminGroup): group to check

    Returns:
        list: List of users

    """

    return User.objects.filter(rbacadminusergroup__group=admin_group).order_by(
        "first_name"
    )


def rbac_get_users_with_role(role):
    """returns a list of all users who have a role, either specifically or
    from having the equivalent generic role. E.g. forums.forum.5.view would
    also return users with forums.forum.view or forums.forum.all"""

    (app, model, model_instance, action) = role_to_parts(role)

    group_roles_specific = RBACGroupRole.objects.filter(
        app=app, model=model, model_id=model_instance
    ).filter(Q(action=action) | Q(action="all"))

    if model_instance:  # check for generic too
        group_roles_higher = RBACGroupRole.objects.filter(
            app=app, model=model, model_id=None
        ).filter(Q(action=action) | Q(action="all"))
    else:
        group_roles_higher = RBACGroupRole.objects.none()

    group_roles = group_roles_higher | group_roles_specific

    groups = group_roles.distinct("group").values("group")

    user_ids = (
        RBACUserGroup.objects.filter(group__in=groups)
        .distinct("member")
        .values("member")
    )

    return User.objects.filter(id__in=user_ids).order_by("first_name")


def rbac_get_users_with_exact_role(role):
    """returns a list of all users who have a role specifically,
    NOT from having the equivalent generic role. E.g. forums.forum.5.view would
    not also return users with forums.forum.view or forums.forum.all"""

    (app, model, model_instance, action) = role_to_parts(role)

    group_roles_specific = RBACGroupRole.objects.filter(
        app=app,
        model=model,
        model_id=model_instance,
        action=action,
    )

    groups = group_roles_specific.distinct("group").values("group")

    user_ids = (
        RBACUserGroup.objects.filter(group__in=groups)
        .distinct("member")
        .values("member")
    )

    return User.objects.filter(id__in=user_ids).order_by("first_name")


def rbac_admin_tree_access(user):
    """returns a list of where in the tree a user had admin access.

    Args:
        user(User): standard user object

    Returns:
        list:   list of trees
    """

    groups = RBACAdminUserGroup.objects.filter(member=user).values_list("group")
    matches = (
        RBACAdminTree.objects.filter(group__in=groups)
        .distinct("tree")
        .values_list("tree")
    )
    return [item for match in matches for item in match]


def rbac_user_has_admin_tree_access(user, admin_tree):
    """returns whether a user has admin access to this exact part of the tree.

    Used initially by orgs for club admin so only checks the provided path, not anything higher.

    e.g. if user has admin.b this will not match on admin.b.c

    Args:
        user(User): standard user object
        admin_tree(str): tree path to check

    Returns:
        boolean
    """

    return (
        RBACAdminUserGroup.objects.filter(member=user)
        .filter(group__rbacadmintree__tree=admin_tree)
        .exists()
    )


def rbac_group_id_from_name(name_qualifier, name_item):
    """returns the id of a group based upon its name

    Args:
        name_qualifier(Str): Group qualifier
        name_item(Str): Group name

    Returns:
        id:   group id
    """

    group = (
        RBACGroup.objects.filter(name_qualifier=name_qualifier)
        .filter(name_item=name_item)
        .first()
    )

    return group.id if group else None


def rbac_show_admin(request):
    """Decide whether to show the admin link on the main template to this user

    Args:
        request(Request): Standard request object

    Returns:
        boolean:   True to show it, False to not show it
    """

    # Show admin menu if user has any RBAC role that is not generated
    return (
        RBACUserGroup.objects.filter(member=request.user)
        .exclude(group__name_qualifier__icontains="generated")
        .exists()
    )


def rbac_user_has_any_model(member, app, model):
    """check if a user has access to any model in a role

    Args:
        member(User): standard user object
        app(str): app to check
        model(str): model to check

    Returns:
        bool: True or False for user role
    """

    return (
        RBACGroupRole.objects.filter(app=app, model=model)
        .filter(group__rbacusergroup__member=member)
        .exists()
    )


def rbac_admin_add_tree_to_group(group, tree):
    """Add tree to an admin group

    Args:
        group(RBACAdminGroup): group to update
        tree(str): Tree tp add

    Returns:
        Nothing
    """
    if not RBACAdminTree.objects.filter(group=group, tree=tree).exists():
        RBACAdminTree(group=group, tree=tree).save()
