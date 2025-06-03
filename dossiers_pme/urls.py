# dossiers_pme/urls.py
from django.urls import path
from . import views

app_name = 'dossiers_pme' # Important pour le namespacing des URLs

urlpatterns = [
    # Exemple: path('', views.liste_dossiers_view, name='liste_dossiers'), # Si on veut une page listant uniquement les dossiers
    path('<int:pk>/', views.detail_dossier_pme_view, name='detail_dossier'),
    # Plus tard, nous pourrons ajouter des URLs pour la création, modification, etc.
]