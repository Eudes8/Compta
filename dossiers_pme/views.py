# dossiers_pme/views.py
from django.shortcuts import render, get_object_or_404, redirect # redirect si besoin
from django.contrib.auth.decorators import login_required # Si vos vues sont protégées
from django.urls import reverse # Pour générer des URLs dans le contexte
from django.utils import timezone # Utile pour les dates
from datetime import date, timedelta
from django.db.models import Sum, Count, Value, DecimalField
from django.db.models.functions import Coalesce # Très utile pour les agrégations

from .models import DossierPME
# Import des modèles de l'application comptabilite
from comptabilite.models import EcritureComptable, LigneEcriture, CompteComptablePME 
# Note: CompteComptablePME est importé mais pas directement utilisé dans le calcul ci-dessous,
# car LigneEcriture.compte_general est déjà une instance de CompteComptablePME.
# Il pourrait être utile si vous voulez afficher le plan comptable spécifique au dossier.

# --- Vue pour lister les dossiers (Exemple, si vous en avez une) ---
@login_required # Exemple de décorateur
def liste_dossiers_pme_view(request):
    dossiers = DossierPME.objects.filter(est_actif=True).order_by('nom_dossier')
    # Vous pourriez vouloir filtrer par utilisateur ou cabinet ici
    context = {
        'dossiers': dossiers,
        'page_title': "Liste des Dossiers PME",
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': 'Tableau de Bord Global'},
            {'label': 'Liste des Dossiers PME'},
        ]
    }
    return render(request, 'dossiers_pme/liste_dossiers.html', context)


# --- Vue pour le détail d'un dossier PME (CORRIGÉE) ---
@login_required # Exemple de décorateur
def detail_dossier_pme_view(request, pk):
    dossier = get_object_or_404(DossierPME, pk=pk)

    # --- KPIs pour le Tableau de Bord du Dossier ---
    # Vous pouvez les rendre plus dynamiques (ex: chercher dans un modèle Tache ou Echeance)
    prochain_jalon_compta = "Déclaration TVA - 15/ProchainMois" # Placeholder
    taches_ouvertes_count = 0 # Placeholder

    # Définition de l'année N (par exemple, l'année actuelle ou l'année du dernier exercice clôturé)
    # Pour cet exemple, utilisons l'année actuelle.
    # Pour une application réelle, vous auriez un concept d'"exercice courant" pour le dossier.
    annee_n = date.today().year 
    # Vous pouvez aussi permettre à l'utilisateur de sélectionner l'année via la requête GET
    # annee_selectionnee = request.GET.get('annee', date.today().year)
    # try:
    #     annee_n = int(annee_selectionnee)
    # except ValueError:
    #     annee_n = date.today().year


    # --- Calcul du Chiffre d'Affaires Année N ---
    ca_annee_n = "N/A" # Initialisation
    try:
        # Les produits sont généralement les comptes de la classe 7 (SYSCOHADA)
        # Le CA est la somme des crédits (ventes) moins les débits (annulations, retours) sur ces comptes.
        lignes_produits = LigneEcriture.objects.filter(
            ecriture__dossier_pme=dossier,
            ecriture__date_ecriture__year=annee_n,
            # --- CORRECTION ICI ---
            compte_general__numero_compte__startswith='7' 
            # --- FIN CORRECTION ---
        ).aggregate(
            total_credits=Coalesce(Sum('credit'), Value(0, output_field=DecimalField())),
            total_debits=Coalesce(Sum('debit'), Value(0, output_field=DecimalField()))
        )
        
        ca_annee_n = lignes_produits['total_credits'] - lignes_produits['total_debits']
    except Exception as e:
        # Il est bon de logguer cette erreur pour le débogage
        print(f"Erreur calcul CA pour dossier {dossier.pk} annee {annee_n}: {e}")
        # Vous pourriez vouloir afficher un message à l'utilisateur ou simplement laisser "N/A"
        # messages.warning(request, "Impossible de calculer le chiffre d'affaires pour l'année sélectionnée.")


    # --- Calcul du Résultat Net Année N (Simplifié) ---
    resultat_net_annee_n = "N/A" # Initialisation
    try:
        # Total des Produits (Classe 7)
        total_produits = ca_annee_n # On réutilise le calcul du CA si le CA = Total Produits

        # Total des Charges (Classe 6)
        # Les charges sont la somme des débits (achats, frais) moins les crédits (annulations)
        lignes_charges = LigneEcriture.objects.filter(
            ecriture__dossier_pme=dossier,
            ecriture__date_ecriture__year=annee_n,
            # --- CORRECTION ICI ---
            compte_general__numero_compte__startswith='6'
            # --- FIN CORRECTION ---
        ).aggregate(
            total_credits=Coalesce(Sum('credit'), Value(0, output_field=DecimalField())),
            total_debits=Coalesce(Sum('debit'), Value(0, output_field=DecimalField()))
        )
        total_charges = lignes_charges['total_debits'] - lignes_charges['total_credits']
        
        # Résultat = Total Produits - Total Charges
        # Assurez-vous que ca_annee_n n'est pas "N/A"
        if isinstance(ca_annee_n, (int, float, DecimalField().to_python_value(0).__class__)) and \
           isinstance(total_charges, (int, float, DecimalField().to_python_value(0).__class__)):
            resultat_net_annee_n = ca_annee_n - total_charges
        else:
            # Si ca_annee_n est "N/A", le résultat net ne peut pas être calculé proprement
            resultat_net_annee_n = "N/A"

    except Exception as e:
        print(f"Erreur calcul Résultat Net pour dossier {dossier.pk} annee {annee_n}: {e}")
        # messages.warning(request, "Impossible de calculer le résultat net pour l'année sélectionnée.")


    context = {
        'dossier': dossier,
        'page_title': f"Tableau de Bord - {dossier.nom_dossier}",
        'annee_concernee': annee_n, # Pour afficher l'année dans le template
        
        # KPIs
        'kpi_prochain_jalon_compta': prochain_jalon_compta,
        'kpi_taches_ouvertes_count': taches_ouvertes_count,
        'kpi_ca_annee_n': ca_annee_n,
        'kpi_resultat_net_annee_n': resultat_net_annee_n,
        
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': 'Tableau de Bord Global'},
            # Si vous avez une liste de dossiers, vous pouvez l'ajouter ici
            # {'url': reverse('dossiers_pme:liste_dossiers'), 'label': 'Mes Dossiers'}, 
            {'label': dossier.nom_dossier}, # La page actuelle n'a pas d'URL cliquable dans le breadcrumb
        ]
    }
    return render(request, 'dossiers_pme/detail_dossier.html', context)

# --- Vue pour créer un DossierPME (Exemple) ---
# from .forms import DossierPMEForm # Vous auriez besoin d'un formulaire
# @login_required
# def creer_dossier_pme_view(request):
#     if request.method == 'POST':
#         form = DossierPMEForm(request.POST, request.FILES) # request.FILES si vous avez des uploads
#         if form.is_valid():
#             dossier = form.save(commit=False)
#             # dossier.cree_par = request.user # Si vous voulez lier à l'utilisateur
#             dossier.save()
#             messages.success(request, f"Le dossier '{dossier.nom_dossier}' a été créé avec succès.")
#             return redirect('dossiers_pme:detail_dossier', pk=dossier.pk)
#     else:
#         form = DossierPMEForm()
#     context = {
#         'form': form,
#         'page_title': "Créer un Nouveau Dossier PME",
#         'niveaux_breadcrumb': [
#             {'url': reverse('core:home'), 'label': 'Tableau de Bord Global'},
#             # {'url': reverse('dossiers_pme:liste_dossiers'), 'label': 'Mes Dossiers'},
#             {'label': 'Créer Dossier'},
#         ]
#     }
#     return render(request, 'dossiers_pme/form_dossier.html', context)

# --- Vue pour modifier un DossierPME (Exemple) ---
# @login_required
# def modifier_dossier_pme_view(request, pk):
#     dossier = get_object_or_404(DossierPME, pk=pk)
#     # TODO: Vérifier les permissions de l'utilisateur sur ce dossier
#     if request.method == 'POST':
#         form = DossierPMEForm(request.POST, request.FILES, instance=dossier)
#         if form.is_valid():
#             form.save()
#             messages.success(request, f"Le dossier '{dossier.nom_dossier}' a été modifié.")
#             return redirect('dossiers_pme:detail_dossier', pk=dossier.pk)
#     else:
#         form = DossierPMEForm(instance=dossier)
#     context = {
#         'form': form,
#         'dossier': dossier,
#         'page_title': f"Modifier: {dossier.nom_dossier}",
#         'niveaux_breadcrumb': [
#             {'url': reverse('core:home'), 'label': 'Tableau de Bord Global'},
#             # {'url': reverse('dossiers_pme:liste_dossiers'), 'label': 'Mes Dossiers'},
#             {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
#             {'label': 'Modifier'},
#         ]
#     }
#     return render(request, 'dossiers_pme/form_dossier.html', context)