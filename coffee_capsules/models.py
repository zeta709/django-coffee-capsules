from django.db import models
from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

class Capsule(models.Model):
	name = models.CharField(max_length=64, unique=True)
	price = models.IntegerField()
	# TODO: description(text, url?)
	def __unicode__(self):
		return self.name
	def get_price(self):
		return self.price
	class Meta:
		ordering = ['pk']

class Purchase(models.Model):
	name = models.CharField(max_length=64)
	begin_date = models.DateTimeField()
	end_date = models.DateTimeField()
	is_closed = models.BooleanField(default=False)
	def __unicode__(self):
		return self.name
	def clean(self):
		if self.begin_date >= self.end_date:
			raise ValidationError('begin_date >= end_date')
		if self.end_date <= timezone.now():
			raise ValidationError('end_date is not in the future')

class PurchaseItem(models.Model):
	purchase = models.ForeignKey(Purchase)
	capsule = models.ForeignKey(Capsule, related_name='+')
	price = models.IntegerField() # 'Since price can be changed, each PurchaseItem has price at the Purchase moment'
	quantity_accepted = models.IntegerField(default=0, editable=False)
	quantity_grouped = models.IntegerField(default=0, editable=False)
	quantity_queued = models.IntegerField(default=0, editable=False)
	class Meta:
		unique_together = (("purchase", "capsule"))
	def __unicode__(self):
		return self.purchase.__unicode__() + ": " + self.capsule.__unicode__()

class Request(models.Model):
	purchaseitem = models.ForeignKey(PurchaseItem)
	user = models.ForeignKey(User, related_name='+')
	quantity_accepted = models.IntegerField(default=0, editable=False)
	quantity_grouped = models.IntegerField(default=0, editable=False)
	quantity_queued = models.IntegerField(default=0)
	date = models.DateTimeField(auto_now=True)
	#class Meta:
	#	unique_together = (("purchaseitem", "user"))

class RequestGroup(models.Model):
	purchaseitem = models.ForeignKey(PurchaseItem, editable=False)
	priority = models.BooleanField(default=False, editable=False)
	quantity = models.IntegerField(default=0, editable=False)
	is_accepted = models.BooleanField(default=False, editable=False)
	date = models.DateTimeField(editable=False)
	def clean(self):
		if self.quantity%10 != 0:
			raise ValidationError('quantity of RequestGroup should be multiples of 10')

@receiver(signals.post_save, sender=Request)
@transaction.commit_on_success
def insert_RequestGroup(sender, instance, created, **kwargs):
	if created == False:
		return
	g_unit = 10 # TODO: settings
	if instance.quantity_accepted > 0 or instance.quantity_grouped > 0:
		print("DEBUG: ERROR")
	instance.purchaseitem.quantity_queued += instance.quantity_queued
	instance.purchaseitem.save()
	if instance.quantity_queued >= g_unit:
		mypr = True
		rgqty = (instance.quantity_queued//g_unit)*g_unit
		instance.purchaseitem.quantity_queued -= rgqty
		instance.purchaseitem.quantity_grouped += rgqty
		instance.purchaseitem.save()
		instance.quantity_queued -= rgqty
		instance.quantity_grouped += rgqty
		instance.save()
		rg = RequestGroup(purchaseitem=instance.purchaseitem, priority=mypr, quantity=rgqty, is_accepted=False, date=instance.date)
		rg.save()
	# remainders
	requests = Request.objects.filter(purchaseitem=instance.purchaseitem, quantity_queued__gt=0).order_by('date')
	qtysum = requests.aggregate(models.Sum('quantity_queued'))['quantity_queued__sum']
	if qtysum >= g_unit:
		mypr = False
		rgqty = (qtysum//g_unit)*g_unit
		instance.purchaseitem.quantity_queued -= rgqty
		instance.purchaseitem.quantity_grouped += rgqty
		instance.purchaseitem.save()
		tmp = rgqty
		for r in requests.all():
			mod = min(r.quantity_queued, tmp)
			r.quantity_queued -= mod
			r.quantity_grouped += mod
			r.save()
			tmp -= mod
			if tmp == 0:
				break
		rg = RequestGroup(purchaseitem=instance.purchaseitem, priority=mypr, quantity=rgqty, is_accepted=False, date=instance.date)
		rg.save()

@receiver(signals.post_save, sender=RequestGroup)
@transaction.commit_on_success
def update_PurchaseItem(sender, instance, created, **kwargs):
	if created == False:
		return
	pass
