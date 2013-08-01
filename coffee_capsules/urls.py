from django.conf.urls import patterns, url

from coffee_capsules import views

urlpatterns = patterns('',
	url(r'^$', views.index, name='index'),
	url(r'^(?P<event_id>\d+)/$', views.detail, name='detail'),
)
