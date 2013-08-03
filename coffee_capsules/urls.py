from django.conf.urls import patterns, url

from coffee_capsules import views

urlpatterns = patterns('',
	url(r'^$', views.IndexView.as_view(), name='index'),
	url(r'^new_purchase/$', views.new_purchase, name='new_purchase'),
	url(r'^(?P<myid>\d+)/$', views.detail, name='detail'),
	url(r'^(?P<myid>\d+)/purchase_request/$', views.purchase_request, name='purchase_request'),
)
