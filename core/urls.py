# core/urls.py
from django.urls import path
from . import views

app_name = 'core'  # Important pour le namespacing (ex: 'core:home')

urlpatterns = [
    # Page d'accueil globale (Tableau de Bord Global)
    path('', views.home_view, name='home'),
    # Ajoutez d'autres URLs pour l'application 'core' ici si nécessaire
    # Par exemple, plus tard, pour les pages de connexion/déconnexion personnalisées si vous les mettez dans 'core'
    # path('login/', views.custom_login_view, name='login'),
    # path('logout/', views.custom_logout_view, name='logout'),
]