# core/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from dossiers_pme.models import DossierPME # Pour afficher la liste des dossiers PME

@login_required # La page d'accueil globale nécessite aussi d'être connecté
def home_view(request):
    # Récupérer la liste des DossierPME pour affichage sur le tableau de bord global
    # Ceci correspond à votre plan: "Affichage de la liste des DossierPME sur le tableau de bord global."
    try:
        dossiers_pme = DossierPME.objects.all().order_by('nom_dossier') # Ou nom_pme
    except Exception as e:
        # Gérer l'erreur si besoin, pour l'instant on passe une liste vide
        dossiers_pme = []
        # logger.error(f"Erreur de récupération des dossiers PME pour home_view: {e}")

    context = {
        'page_title': "Tableau de Bord Global - OPTIMA GEST PME",
        'dossiers_pme': dossiers_pme,
        # Plus tard, vous ajouterez des KPIs globaux ici
        # 'kpi_total_dossiers': DossierPME.objects.count(),
        # 'kpi_taches_globales': ...
    }
    return render(request, 'core/home.html', context)

# Plus tard, si vous mettez les vues de connexion/déconnexion ici :
# def custom_login_view(request):
#     # Votre logique de connexion
#     pass

# def custom_logout_view(request):
#     # Votre logique de déconnexion
#     pass