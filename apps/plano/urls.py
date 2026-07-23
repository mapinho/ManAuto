from django.urls import path

from . import views

app_name = "plano"

urlpatterns = [
    path("cronograma/", views.cronograma, name="cronograma"),
    path("cronograma/recalcular/", views.recalcular, name="recalcular"),
    path("agenda/", views.agenda, name="agenda"),
]
