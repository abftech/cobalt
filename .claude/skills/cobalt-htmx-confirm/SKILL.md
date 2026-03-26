---
name: cobalt-htmx-confirm
description: >-
  Add a SweetAlert2 confirmation dialog to a Cobalt template. Use this whenever the user
  wants to confirm before an action, warn before submitting, add a delete button, or prevent
  accidental actions — even if they don't mention SweetAlert2 or HTMX. Triggers include
  "add a confirm step", "warn the user before they delete", "are you sure dialog",
  "confirmation popup", or any time a destructive or irreversible action needs a prompt.
  This replaces any use of the browser's native confirm().
argument-hint: [description of the action being confirmed]
---

Add a SweetAlert2 confirmation dialog following the Cobalt pattern.

## Rules
- **Never use the browser's native `confirm()`** for destructive actions.
- Load SweetAlert2 in `{% block footer %}`.
- Trigger HTMX programmatically via `htmx.ajax()` inside the `.then()` callback.
- The button calls the JS function directly — **no `hx-post` on the button itself**.
- If the page manages its own state and doesn't need the "leave page?" prompt, add `<span id="ignore_cobalt_save" hidden></span>` anywhere in the template.

## Template pattern

```html
{% load static %}
{% block footer %}
    <script src="{% static "assets/js/plugins/sweetalert2.js" %}"></script>
    <script>
        function confirmAction(recordId) {
            Swal.fire({
                title: 'Are you sure?',
                text: 'This cannot be undone.',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#3085d6',
                confirmButtonText: 'Yes, do it'
            }).then((result) => {
                if (result.isConfirmed) {
                    htmx.ajax('POST', '{% url "app:some_view" %}', {
                        target: '#some-div',
                        values: {record_id: recordId}  // pass context as needed
                    });
                }
            });
        }
    </script>
{% endblock footer %}
```

Button (no `hx-post` — call the JS function directly):
```html
<button onclick="confirmAction({{ record.id }})">Delete</button>
```

If the page has multiple confirm actions (e.g. delete + archive), give each its own function with a descriptive name rather than reusing `confirmAction`.

Now add a confirmation dialog for: $ARGUMENTS
