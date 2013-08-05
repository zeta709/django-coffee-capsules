from django import forms
from django.forms.extras import SelectDateWidget
from django.contrib.admin import widgets

from coffee_capsules.models import Capsule, Purchase, PurchaseItem, Request
from coffee_capsules.widgets import SelectedReadonly

# http://stackoverflow.com/questions/15643019/
class PurchaseForm(forms.ModelForm):
	class Meta:
		model = Purchase
	def __init__(self, *args, **kwargs):
		super(PurchaseForm, self).__init__(*args, **kwargs)
		self.fields['begin_date'].widget = widgets.AdminSplitDateTime()
		self.fields['end_date'].widget = widgets.AdminSplitDateTime()

class MyRequestForm(forms.ModelForm):
	class Meta:
		model = Request
		#fields = ('purchaseitem','user', 'quantity_queued',)
		#readonly_fields = ('purchaseitem','user',)
		exclude = ('user',)
		widgets = {
			'purchaseitem': SelectedReadonly(),
			#'user': SelectedReadonly(),
			#'user': forms.HiddenInput(),
			#'user': forms.Select(),
			#'user': forms.TextInput(),
		}
	def __init__(self, *args, **kwargs):
		super(MyRequestForm, self).__init__(*args, **kwargs)
		self.fields['purchaseitem'].widget.attrs['readonly'] = 'readonly'
		self.fields['purchaseitem'].label = 'Item'
		self.fields['quantity_queued'].label = 'Quantity'
	
	def clean_quantity_queued(self):
		qty = self.cleaned_data['quantity_queued']
		my_u_unit = self.cleaned_data['purchaseitem'].purchase.u_unit
		if qty < 0:
			raise forms.ValidationError("Values cannot be negative.")
		if qty%my_u_unit != 0:
			raise forms.ValidationError('Each value should be multiples of ' + str(my_u_unit))
		return qty

	def clean(self):
		cleaned_data = super(MyRequestForm, self).clean()
		purchaseitem = cleaned_data.get("purchaseitem")
		purchase = purchaseitem.purchase
		if purchase.is_not_open():
			raise forms.ValidationError("The purchase is not yet open.")
		if purchase.is_ended():
			raise forms.ValidationError("The purchase is aleady ended.")
		if purchase.is_closed:
			raise forms.ValidationError("The purchase is closed.")
		return cleaned_data

