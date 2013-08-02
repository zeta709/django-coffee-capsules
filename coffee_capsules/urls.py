from django.conf.urls import patterns, url

from coffee_capsules import views

urlpatterns = patterns('',
	url(r'^$', views.IndexView.as_view(), name='index'),
	url(r'^(?P<myid>\d+)/$', views.detail, name='detail'),
)
