from django.db import models
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
	def clean(self):
		if self.price < 0:
			raise ValidationError('price < 0')

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
	#def quantity_accepted(self):
	#	return self.request_set.aggregate(models.Sum('quantity_accepted'))['quantity_accepted__sum']
	#def quantity_grouped(self):
	#	return self.request_set.aggregate(models.Sum('quantity_grouped'))['quantity_grouped__sum']
	#def quantity_queued(self):
	#	return self.request_set.aggregate(models.Sum('quantity_queued'))['quantity_queued__sum']
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
	#	unique_together = (("purchaseitem", "user"))

class RequestGroup(models.Model):
	purchaseitem = models.ForeignKey(PurchaseItem, editable=False)
	priority = models.BooleanField(default=False, editable=False)
	quantity_accepted = models.IntegerField(default=0, editable=False)
	quantity_grouped = models.IntegerField(default=0, editable=False)
	date = models.DateTimeField(editable=False)
	# TODO: many-to-many fields??
	def clean(self):
		if self.quantity%10 != 0:
			raise ValidationError('quantity of RequestGroup should be multiples of 10')

class RequestGroupItem(models.Model):
	requestgroup = models.ForeignKey(RequestGroup)
	request = models.ForeignKey(Request)
	quantity = models.IntegerField()

################################################################################
# auto-update-other-fields functons (similar to trigger)
################################################################################
from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver

@receiver(signals.post_save, sender=Request)
@transaction.commit_on_success
def group_request(sender, instance, created, **kwargs):
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
		rg = RequestGroup(purchaseitem=instance.purchaseitem, priority=mypr, quantity_grouped=rgqty, date=instance.date)
		rg.save()
		rgitem = RequestGroupItem(requestgroup=rg, request=instance, quantity=rgqty)
		rgitem.save()
		accept_request(rg)
	# remainders
	requests = Request.objects.filter(purchaseitem=instance.purchaseitem, quantity_queued__gt=0).order_by('date')
	qtysum = requests.aggregate(models.Sum('quantity_queued'))['quantity_queued__sum']
	if qtysum >= g_unit:
		mypr = False
		rgqty = (qtysum//g_unit)*g_unit
		instance.purchaseitem.quantity_queued -= rgqty
		instance.purchaseitem.quantity_grouped += rgqty
		instance.purchaseitem.save()
		rg = RequestGroup(purchaseitem=instance.purchaseitem, priority=mypr, quantity_grouped=rgqty, date=instance.date)
		rg.save()
		tmp = rgqty
		for r in requests.all():
			mod = min(r.quantity_queued, tmp)
			r.quantity_queued -= mod
			r.quantity_grouped += mod
			r.save()
			rgitem = RequestGroupItem(requestgroup=rg, request=r, quantity=mod)
			rgitem.save()
			tmp -= mod
			if tmp == 0:
				break
		if tmp != 0:
			print('ERROR')
		accept_request(rg)

def accept_request(instance):
	p_unit = 50 # TODO: settings
	rgs = RequestGroup.objects.filter(purchaseitem__purchase=instance.purchaseitem.purchase, quantity_grouped__gt=0).order_by('date')
	qtysum = rgs.aggregate(models.Sum('quantity_grouped'))['quantity_grouped__sum']
	if qtysum >= p_unit:
		p_qty = (qtysum//p_unit)*p_unit
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
			tmp -= mod
			if tmp == 0:
				break
		if tmp != 0:
			print('ERROR')
