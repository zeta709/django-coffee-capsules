from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Capsule(models.Model):
    name = models.CharField(max_length=64, unique=True)
    price = models.IntegerField()
    # TODO: description(text, url?)

    class Meta:
        ordering = ['pk']

    def __unicode__(self):
        return self.name

    def get_price(self):
        return self.price

    def clean(self):
        if self.price < 0:
            raise ValidationError('price < 0')


class Purchase(models.Model):
    name = models.CharField(max_length=64)
    begin_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_closed = models.BooleanField(default=False)
    g_unit = models.PositiveIntegerField('Group unit', default=10,
                                         help_text="Each purchase item"
                                         " is available in"
                                         " units of this value."
                                         " (default: 10)")
    p_unit = models.PositiveIntegerField('Purchase unit', default=50,
                                         help_text="Sum of all purchase items"
                                         " should be in units of this value."
                                         " (default: 50)")
    u_unit = models.PositiveIntegerField('User unit', default=1,
                                         help_text="Each user can request"
                                         " each item in unit of this value.")

    def is_not_open(self):
        return self.begin_date > timezone.now()

    def is_ended(self):
        return timezone.now() > self.end_date

    def __unicode__(self):
        return self.name

    def clean(self):
        if self.begin_date >= self.end_date:
            raise ValidationError('begin_date >= end_date')
        if self.end_date <= timezone.now():
            raise ValidationError('end_date is not in the future')
        if self.p_unit % self.g_unit != 0:
            raise ValidationError(
                "Purchase unit sholud be multiples of group unit")


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase)
    capsule = models.ForeignKey(Capsule, related_name='+')
    # 'Since price can be changed,
    # each PurchaseItem has price at the Purchase moment'
    price = models.IntegerField()
    quantity_accepted = models.IntegerField(default=0, editable=False)
    quantity_grouped = models.IntegerField(default=0, editable=False)
    quantity_queued = models.IntegerField(default=0, editable=False)
    #def quantity_accepted(self):
    #    return self.request_set.aggregate(
    #        models.Sum('quantity_accepted'))['quantity_accepted__sum']
    #def quantity_grouped(self):
    #    return self.request_set.aggregate(
    #        models.Sum('quantity_grouped'))['quantity_grouped__sum']
    #def quantity_queued(self):
    #    return self.request_set.aggregate(
    #        models.Sum('quantity_queued'))['quantity_queued__sum']

    class Meta:
        unique_together = (("purchase", "capsule"))

    def __unicode__(self):
        return self.purchase.__unicode__() + ": " + self.capsule.__unicode__()

    def clean(self):
        if self.price < 0:
            raise ValidationError('price < 0')
        if self.quantity_accepted < 0:
            raise ValidationError('quantity_accepted < 0')
        if self.quantity_grouped < 0:
            raise ValidationError('quantity_grouped < 0')
        if self.quantity_queued < 0:
            raise ValidationError('quantity_queued < 0')


class Request(models.Model):
    purchaseitem = models.ForeignKey(PurchaseItem)
    user = models.ForeignKey(User, related_name='+')
    quantity_accepted = models.IntegerField(default=0, editable=False)
    quantity_grouped = models.IntegerField(default=0, editable=False)
    quantity_queued = models.IntegerField(default=0)
    date = models.DateTimeField(auto_now=True)
    #class Meta:
    #    unique_together = (("purchaseitem", "user"))

    def clean(self):
        my_u_unit = self.purchaseitem.purchase.u_unit
        if self.quantity_queued % my_u_unit != 0:
            raise ValidationError(
                "Each item should be multiles of %s" % my_u_unit)


class RequestGroup(models.Model):
    purchaseitem = models.ForeignKey(PurchaseItem, editable=False)
    priority = models.BooleanField(default=False, editable=False)
    quantity_accepted = models.IntegerField(default=0, editable=False)
    quantity_grouped = models.IntegerField(default=0, editable=False)
    date = models.DateTimeField(editable=False)
    # TODO: many-to-many fields??

    def clean(self):
        my_g_unit = self.purchaseitem.purchase.g_unit
        if self.quantity % my_g_unit != 0:
            raise ValidationError("quantity of RequestGroup"
                                  " should be multiples of group unit.")


class RequestGroupItem(models.Model):
    requestgroup = models.ForeignKey(RequestGroup)
    request = models.ForeignKey(Request)
    quantity = models.IntegerField()

##############################################################################
# auto-update-other-fields functons (similar to trigger)
##############################################################################
from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver


@receiver(signals.post_save, sender=Request)
@transaction.commit_on_success
def group_request(sender, instance, created, **kwargs):
    if not created:
        return
    my_g_unit = instance.purchaseitem.purchase.g_unit
    if instance.quantity_accepted > 0 or instance.quantity_grouped > 0:
        print("DEBUG: ERROR")
    instance.purchaseitem.quantity_queued += instance.quantity_queued
    instance.purchaseitem.save()
    if instance.quantity_queued >= my_g_unit:
        mypr = True
        rgqty = (instance.quantity_queued // my_g_unit) * my_g_unit
        instance.purchaseitem.quantity_queued -= rgqty
        instance.purchaseitem.quantity_grouped += rgqty
        instance.purchaseitem.save()
        instance.quantity_queued -= rgqty
        instance.quantity_grouped += rgqty
        instance.save()
        rg = RequestGroup(purchaseitem=instance.purchaseitem,
                          priority=mypr,
                          quantity_grouped=rgqty, date=instance.date)
        rg.save()
        rgitem = RequestGroupItem(requestgroup=rg,
                                  request=instance, quantity=rgqty)
        rgitem.save()
        accept_request(rg)
    # remainders
    requests = Request.objects.filter(purchaseitem=instance.purchaseitem,
                                      quantity_queued__gt=0).order_by('date')
    qtysum = requests.aggregate(models.Sum('quantity_queued'
                                           ))['quantity_queued__sum']
    if qtysum >= my_g_unit:
        mypr = False
        rgqty = (qtysum // my_g_unit) * my_g_unit
        instance.purchaseitem.quantity_queued -= rgqty
        instance.purchaseitem.quantity_grouped += rgqty
        instance.purchaseitem.save()
        rg = RequestGroup(purchaseitem=instance.purchaseitem,
                          priority=mypr, quantity_grouped=rgqty,
                          date=instance.date)
        rg.save()
        tmp = rgqty
        for r in requests.all():
            mod = min(r.quantity_queued, tmp)
            r.quantity_queued -= mod
            r.quantity_grouped += mod
            r.save()
            rgitem = RequestGroupItem(requestgroup=rg, request=r,
                                      quantity=mod)
            rgitem.save()
            tmp -= mod
            if tmp == 0:
                break
        # rof
        if tmp != 0:
            print('ERROR')
        accept_request(rg)


def accept_request(instance):
    my_p_unit = instance.purchaseitem.purchase.p_unit
    rgs = RequestGroup.objects.filter(
        purchaseitem__purchase=instance.purchaseitem.purchase,
        quantity_grouped__gt=0).order_by('date')
    qtysum = rgs.aggregate(models.Sum('quantity_grouped'
                                      ))['quantity_grouped__sum']
    if qtysum >= my_p_unit:
        p_qty = (qtysum // my_p_unit) * my_p_unit
        tmp = p_qty
        for rg in rgs.all():
            mod = min(rg.quantity_grouped, tmp)
            rg.purchaseitem.quantity_grouped -= mod
            rg.purchaseitem.quantity_accepted += mod
            rg.purchaseitem.save()
            rg.quantity_grouped -= mod
            rg.quantity_accepted += mod
            rg.save()
            rgitems = RequestGroupItem.objects.filter(requestgroup=rg)
            tmp2 = mod
            for rgitem in rgitems.all():
                mod2 = min(rgitem.quantity, tmp2)
                rgitem.request.quantity_grouped -= mod2
                rgitem.request.quantity_accepted += mod2
                rgitem.request.save()
                tmp2 -= mod2
            # rof
            tmp -= mod
            if tmp == 0:
                break
        # rof
        if tmp != 0:
            print('ERROR')
