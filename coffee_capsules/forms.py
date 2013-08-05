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
		print(self.fields['purchaseitem'].widget)

