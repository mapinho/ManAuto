from django.urls import path

from . import views

app_name = "plano"

urlpatterns = [
    path("", views.cronograma, name="cronograma"),
    path("recalcular/", views.recalcular, name="recalcular"),
]
