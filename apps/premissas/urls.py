from django.urls import path

from . import views

app_name = "premissas"

urlpatterns = [
    path("", views.index, name="index"),
    path("oficina/<int:oficina_id>/indices/", views.atualizar_indices, name="atualizar_indices"),
    path("oficina/<int:oficina_id>/disp/", views.atualizar_disp, name="atualizar_disp"),
    path("calendario/mes/", views.atualizar_calendario_mes, name="atualizar_calendario_mes"),
    path("calendario/safra/", views.alternar_safra_mes, name="alternar_safra_mes"),
    path("calendario/datas/", views.atualizar_datas_safra, name="atualizar_datas_safra"),
    path("gatilho/<int:classe_id>/", views.atualizar_gatilho, name="atualizar_gatilho"),
    path(
        "classe/<int:classe_id>/unidade/",
        views.atualizar_classe_unidade,
        name="atualizar_classe_unidade",
    ),
]
