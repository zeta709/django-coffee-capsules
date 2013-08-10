"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.test import TestCase

from coffee_capsules.models import Capsule, Purchase, PurchaseItem, Request


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)


def create_capsule():
    Capsule.objects.create(name='C0', price=1000)
    Capsule.objects.create(name='C1', price=1000)
    Capsule.objects.create(name='C2', price=1000)
    Capsule.objects.create(name='C3', price=1000)
    Capsule.objects.create(name='C4', price=1000)


def create_purchase(name):
    purchase = Purchase.objects.create(
        name=name,
        begin_date=timezone.now(),
        end_date=(timezone.now() + datetime.timedelta(days=7)),
        g_unit=10, p_unit=50, u_unit=10,
    )
    all_capsule_list = Capsule.objects.order_by('pk')
    for capsule in all_capsule_list:
        pi = PurchaseItem.objects.create(
            purchase=purchase,
            capsule=capsule,
            price=capsule.price
        )
    # rof
    return purchase


class RequestTest(TestCase):
    def test_bulk_request0(self):
        """
        Test #0
        """
        create_capsule()
        purchase = create_purchase("test0")
        user = User.objects.create()
        pi_list = purchase.purchaseitem_set.all()
        self.assertEqual(len(pi_list), 5)
        request = Request(
            purchaseitem=pi_list[4],
            user=user,
            quantity_queued=10
        )
        request.save()
        request = Request(
            purchaseitem=pi_list[0],
            user=user,
            quantity_queued=10
        )
        request.save()
        request = Request(
            purchaseitem=pi_list[1],
            user=user,
            quantity_queued=10
        )
        request.save()
        request = Request(
            purchaseitem=pi_list[2],
            user=user,
            quantity_queued=10
        )
        request.save()
        request = Request(
            purchaseitem=pi_list[3],
            user=user,
            quantity_queued=10
        )
        request.save()
        pi_list = purchase.purchaseitem_set.all()  # diff with test1
        request = Request(
            purchaseitem=pi_list[4],
            user=user,
            quantity_queued=10
        )
        request.save()
        self.assertEqual(pi_list[4].quantity_accepted, 10)
        self.assertEqual(pi_list[4].quantity_grouped, 10)
        self.assertEqual(pi_list[4].quantity_queued, 0)

    def test_bulk_request1(self):
        """
        Test #1
        """
        create_capsule()
        purchase = create_purchase("test0")
        user = User.objects.create()
        pi_list = purchase.purchaseitem_set.all()
        self.assertEqual(len(pi_list), 5)
        request = Request(
            purchaseitem=pi_list[4],
            user=user,
            quantity_queued=10
        )
        request.save()
        request = Request(
            purchaseitem=pi_list[0],
            user=user,
            quantity_queued=10
        )
        request.save()
        request = Request(
            purchaseitem=pi_list[1],
            user=user,
            quantity_queued=10
        )
        request.save()
        request = Request(
            purchaseitem=pi_list[2],
            user=user,
            quantity_queued=10
        )
        request.save()
        request = Request(
            purchaseitem=pi_list[3],
            user=user,
            quantity_queued=10
        )
        request.save()
        request = Request(
            purchaseitem=pi_list[4],
            user=user,
            quantity_queued=10
        )
        request.save()
        pi_list = purchase.purchaseitem_set.all()  # diff with test0
        self.assertEqual(pi_list[4].quantity_accepted, 10)
        self.assertEqual(pi_list[4].quantity_grouped, 10)
        self.assertEqual(pi_list[4].quantity_queued, 0)


