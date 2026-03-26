---
name: cobalt-htmx-confirm
description: Add a SweetAlert2 confirmation dialog to a Cobalt template for a destructive HTMX action. Use when adding delete buttons, irreversible actions, or any action that needs a confirmation step.
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
{% block footer %}
    <script src="{% static "assets/js/plugins/sweetalert2.js" %}"></script>
    <script>
        function confirmAction() {
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
                        values: {key: 'value'}
                    });
                }
            });
        }
    </script>
{% endblock footer %}
```

Button (no `hx-post`):
```html
<button onclick="confirmAction()">Delete</button>
```

Now add a confirmation dialog for: $ARGUMENTS
