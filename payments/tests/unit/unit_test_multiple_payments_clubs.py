from threading import Thread

from django.db.transaction import atomic

from organisations.models import Organisation
from payments.models import MemberTransaction, OrganisationTransaction
from payments.views.core import update_account, update_organisation
from tests.test_manager import CobaltTestManagerUnit
from utils.models import Lock

AMOUNT = 1.0


def _helper_thread_function(index, organisation, count):
    """helper to run in multiple threads"""

    for loop in range(count):
        update_organisation(
            organisation=organisation,
            amount=AMOUNT,
            description=f"Parallel Test Thread: {index}. Count: {loop}",
            payment_type="Refund",
        )


class ClubMultiPaymentTests:
    """Test for issues with multiple updates happening close together"""

    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager

    def account_update(self):
        """Tests for the account update"""

        # Run a bunch of threads concurrently

        organisation = Organisation.objects.first()

        thread_count = 5
        repeats = 10

        threads = []

        for index in range(thread_count):
            this_thread = Thread(
                target=_helper_thread_function, args=[index, organisation, repeats]
            )
            threads.append(this_thread)

        # Start all threads
        for this_thread in threads:
            this_thread.start()

        # Wait for all of them to finish
        for this_thread in threads:
            this_thread.join()

        # Check results
        results = OrganisationTransaction.objects.filter(
            organisation=organisation
        ).order_by("pk")

        expected_balance = AMOUNT
        errors = []

        for result in results:
            if result.balance != expected_balance:
                errors.append(
                    f"ID: {result.pk}. Expected {expected_balance}, got {result.balance}"
                )
            expected_balance += AMOUNT

        if len(results) != thread_count * repeats:
            errors.append(
                f"Expected to find {thread_count * repeats} transactions. Found {len(results)}"
            )

        self.manager.save_results(
            status=not errors,
            test_name="Multiple concurrent calls to update_organisation",
            test_description=f"Run multiple thread to update organisation {organisation}. Should be processed in order.",
            output=f"Errors found: {errors}",
        )
