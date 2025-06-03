# comptabilite/urls.py
from django.urls import path
from . import views, views_sage_grid

app_name = 'comptabilite'

urlpatterns = [
    # Tableau de bord comptable (tableau de bord principal de la compta pour un dossier)
    path('dossier/<int:dossier_pk>/', views.tableau_bord_compta_view, name='tableau_bord_compta'),

    # ... (vos URLs existantes pour le plan_comptable, CRUDs ComptePME, Journal, chargement de plan etc.)

    # Saisie des Écritures
    path('dossier/<int:dossier_pk>/saisie/selectionner-journal/', 
         views.saisie_selection_journal_periode_view, 
         name='saisie_selection_journal_periode'),
    
    path('dossier/<int:dossier_pk>/journal/<int:journal_pk>/<int:annee>/<int:mois>/saisie-piece/', 
         views.saisie_piece_view, 
         name='saisie_piece'),

    # URLs spécifiques pour les actions HTMX sur la saisie de pièce

    # Nouvelle URL AJAX pour l'ajout de ligne (corrigée)
    path('api/dossier/<int:dossier_pk>/journal/<int:journal_pk>/<int:annee>/<int:mois>/enregistrer-ligne-ajax/',
         views.ajouter_ligne_ecriture_ajax,
         name='ajouter_ligne_ecriture_ajax'),

    path('dossier/<int:dossier_pk>/plan-comptable/', views.plan_comptable_view, name='plan_comptable'),

    # Routes CRUD pour les journaux
    path('dossier/<int:dossier_pk>/journaux/', views.liste_journaux_view, name='liste_journaux'),
    path('dossier/<int:dossier_pk>/journaux/creer/', views.creer_journal_view, name='creer_journal'),
    path('journal/<int:journal_pk>/modifier/', views.modifier_journal_view, name='modifier_journal'),
    path('journal/<int:journal_pk>/supprimer/', views.supprimer_journal_view, name='supprimer_journal'),

    path('compte/<int:compte_pk>/toggle-actif/', views.toggle_actif_compte_pme_view, name='toggle_actif_compte_pme'),

    # Routes pour la création et la modification d'un compte PME
    path('dossier/<int:dossier_pk>/compte/creer/', views.creer_modifier_compte_pme_view, name='creer_compte_pme'),    path('compte/<int:compte_pk>/modifier/', views.creer_modifier_compte_pme_view, name='modifier_compte_pme'),
    
    # Saisie interactive style Sage
    path('dossier/<int:dossier_pk>/journal/<int:journal_pk>/<int:annee>/<int:mois>/saisie-sage/', 
         views_sage_grid.saisie_sage_grid_view, 
         name='saisie_sage_grid'),
         
    # API endpoints pour la saisie Sage
    path('api/dossier/<int:dossier_pk>/journal/<int:journal_pk>/<int:annee>/<int:mois>/save-entry/', 
         views_sage_grid.save_sage_grid_entry, 
         name='save_sage_grid_entry'),
      # API endpoints pour la saisie Sage
    path('api/dossier/<int:dossier_pk>/search-accounts/', 
         views_sage_grid.search_accounts_view, 
         name='search_accounts'),
         
    path('api/dossier/<int:dossier_pk>/journal/<int:journal_pk>/piece/<str:piece_number>/<str:direction>/',
         views_sage_grid.get_adjacent_piece,
         name='get_adjacent_piece'),
         
    path('api/dossier/<int:dossier_pk>/journal/<int:journal_pk>/search-pieces/',
         views_sage_grid.search_pieces,
         name='search_pieces'),
         
    path('api/dossier/<int:dossier_pk>/journal/<int:journal_pk>/suggest-piece-number/',
         views_sage_grid.suggest_piece_number,
         name='suggest_piece_number'),
         
    path('api/piece/validate/',
         views_sage_grid.validate_piece,
         name='validate_piece'),
    
    # API pour la recherche de tiers
    path('api/dossier/<int:dossier_pk>/tiers-lookup/', 
         views_sage_grid.tiers_lookup_view, 
         name='api_tiers_lookup'),
    
    # API pour les informations du journal
    path('api/journal/<int:journal_pk>/info/', 
         views_sage_grid.journal_info_view, 
         name='api_journal_info'),
    
    # API pour sauvegarder une pièce
    path('api/piece/save/', 
         views_sage_grid.save_piece_view, 
         name='api_save_piece'),
]