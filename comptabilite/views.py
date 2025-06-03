# comptabilite/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import transaction, IntegrityError
from datetime import date, timedelta
from django.db.models import Sum, Q, Value, DecimalField, F, Max # Ajout de Max
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse # Ajout de JsonResponse
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import json
from django.core.management import call_command
from django.conf import settings
import os
# from django.template.loader import render_to_string # Not used in this specific context
from django.views.decorators.http import require_POST # Pour la nouvelle vue AJAX
from django.core.serializers.json import DjangoJSONEncoder # Pour sérialiser les objets QuerySet
from django.http import Http404 # Import Http404 for explicit handling
import logging # Add this import
logger = logging.getLogger(__name__) # Add this for logging
from dossiers_pme.models import DossierPME
from .models import (
    CompteComptablePME, EcritureComptable, JournalComptable, 
    LigneEcriture, Tiers, TauxDeTaxe, CompteComptableDefaut
)
from .forms import (
    CompteComptablePMEForm,
    SaisieJournalSelectionForm,
    PieceComptableEnTeteForm, 
    LigneEcritureSaisieFormSet,
    LigneEcritureSaisieForm, # Ajout de l'import manquant
    JournalComptableForm,
    TiersForm, 
    TauxDeTaxeForm 
)

def get_mois_courant_dates():
    aujourdhui = date.today()
    premier_jour_mois = aujourdhui.replace(day=1)
    if aujourdhui.month == 12:
        dernier_jour_mois = aujourdhui.replace(year=aujourdhui.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        dernier_jour_mois = aujourdhui.replace(month=aujourdhui.month + 1, day=1) - timedelta(days=1)
    return premier_jour_mois, dernier_jour_mois

def get_next_numero_piece(journal, annee, mois):
    """
    Suggère le prochain numéro de pièce pour un journal et une période donnée.
    Le numéro de pièce ici est celui de l'EcritureComptable "conteneur" du journal/mois.
    """
    # Pour l'EcritureComptable conteneur, on utilise un numéro de pièce fixe par convention.
    # La numérotation séquentielle des "sous-pièces" (lignes avec un numéro de pièce spécifique)
    # se ferait au niveau des lignes ou via une logique différente si nécessaire.
    return f"SJ-{journal.code_journal}-{annee}{mois:02d}"


# --- Fonctions Principales ---
@login_required
def tableau_bord_compta_view(request, dossier_pk):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    current_year = date.today().year
    current_month = date.today().month
    try:
        annee_selectionnee = int(request.GET.get('annee', current_year))
        mois_selectionne = int(request.GET.get('mois', current_month))
        if not (1 <= mois_selectionne <= 12 and 1900 <= annee_selectionnee <= current_year + 10): # Limite étendue
            raise ValueError("Période invalide")
    except (ValueError, TypeError):
        annee_selectionnee = current_year
        mois_selectionne = current_month
        
    premier_jour_periode = date(annee_selectionnee, mois_selectionne, 1)
    if mois_selectionne == 12:
        dernier_jour_periode = date(annee_selectionnee, mois_selectionne, 31)
    else:
        dernier_jour_periode = date(annee_selectionnee, mois_selectionne + 1, 1) - timedelta(days=1)
        
    nombre_comptes_plan = CompteComptablePME.objects.filter(dossier_pme=dossier, est_actif=True).count()
    nombre_journaux_actifs = JournalComptable.objects.filter(dossier_pme=dossier, est_actif=True).count()
    nombre_tiers_actifs = Tiers.objects.filter(dossier_pme=dossier, est_actif=True).count()
    
    nombre_ecritures_periode = 0
    total_debits_periode = Decimal(0)
    total_credits_periode = Decimal(0)
    solde_tresorerie = Decimal(0)
    dernieres_ecritures = EcritureComptable.objects.none() # Initialisation

    try:
        # KPIs pour la période sélectionnée
        ecritures_periode_queryset = EcritureComptable.objects.filter(
            dossier_pme=dossier, 
            date_ecriture__gte=premier_jour_periode, 
            date_ecriture__lte=dernier_jour_periode
        )
        
        nombre_ecritures_periode = ecritures_periode_queryset.count()

        periode_totals = ecritures_periode_queryset.aggregate(
            total_debits=Coalesce(Sum('lignes_ecriture__debit'), Value(Decimal(0), output_field=DecimalField())),
            total_credits=Coalesce(Sum('lignes_ecriture__credit'), Value(Decimal(0), output_field=DecimalField()))
        )
        total_debits_periode = periode_totals['total_debits']
        total_credits_periode = periode_totals['total_credits']
            
        # Dernières écritures (indépendant de la période sélectionnée pour les KPIs)
        dernieres_ecritures = EcritureComptable.objects.filter(
            dossier_pme=dossier
        ).select_related('journal').order_by('-date_ecriture', '-id')[:5]
        
        # Solde de trésorerie global
        comptes_tresorerie_pks = CompteComptablePME.objects.filter(
            dossier_pme=dossier, 
            type_compte__in=['TRESORERIE_ACTIF', 'TRESORERIE_PASSIF'], 
            est_actif=True
        ).values_list('pk', flat=True)
        
        if comptes_tresorerie_pks:
            solde_agg = LigneEcriture.objects.filter(
                compte_general_id__in=list(comptes_tresorerie_pks), 
                ecriture__dossier_pme=dossier
            ).aggregate(
                total_debits=Coalesce(Sum('debit'), Value(Decimal(0), output_field=DecimalField())),
                total_credits=Coalesce(Sum('credit'), Value(Decimal(0), output_field=DecimalField()))
            )
            solde_tresorerie = solde_agg['total_debits'] - solde_agg['total_credits']
            
    except Exception as e:
        messages.warning(request, _("Erreur lors du calcul des KPIs du TDB Compta: %(error)s") % {'error': e})

    # Alertes comptables
    alertes_comptables = []
    count_desequilibrees = 0
    ecritures_desequilibrees = EcritureComptable.objects.filter(dossier_pme=dossier).annotate(
        total_debit_lignes_agg=Coalesce(Sum('lignes_ecriture__debit'), Value(Decimal(0))),
        total_credit_lignes_agg=Coalesce(Sum('lignes_ecriture__credit'), Value(Decimal(0)))
    ).annotate(
        solde_piece_agg=F('total_debit_lignes_agg') - F('total_credit_lignes_agg')
    ).filter(
        Q(solde_piece_agg__gt=Decimal('0.001')) | Q(solde_piece_agg__lt=Decimal('-0.001'))
    )
    
    count_desequilibrees = ecritures_desequilibrees.count()
    
    for ecriture_check in ecritures_desequilibrees[:3]: # Limiter à 3 pour l'affichage détaillé
        alertes_comptables.append({
            'type': 'danger',
            'message': _("Pièce N°%(num)s (%(date)s) déséquilibrée (D: %(debit).2f, C: %(credit).2f).") % {
                'num': ecriture_check.numero_piece or ecriture_check.pk,
                'date': ecriture_check.date_ecriture.strftime('%d/%m/%Y'),
                'debit': ecriture_check.total_debit_lignes_agg,
                'credit': ecriture_check.total_credit_lignes_agg,
            },
            'url': reverse('comptabilite:saisie_piece', kwargs={
                'dossier_pk': dossier.pk,
                'journal_pk': ecriture_check.journal.pk,
                'annee': ecriture_check.date_ecriture.year,
                'mois': ecriture_check.date_ecriture.month,
                'piece_pk': ecriture_check.pk # Ajout du PK de la pièce pour l'édition directe
            })
        })
    
    if count_desequilibrees > 0:
        message_alerte_generale = _("Attention: %(count)s pièce(s) comptable(s) sont déséquilibrées.") % {'count': count_desequilibrees}
        
        # Ajouter le message général si plus de 3 alertes spécifiques ou si aucune alerte spécifique n'est affichée
        if count_desequilibrees > 3 or len(alertes_comptables) == 0:
            alertes_comptables.insert(0, {
                'type': 'warning',
                'message': message_alerte_generale,
                'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}) # Lien vers le TDB pour revoir les alertes
            })

    kpi_prochaine_echeance_valeur = "15/" + (premier_jour_periode + timedelta(days=45)).strftime("%m") # Exemple
    kpi_prochaine_echeance_libelle = _("Déclaration TVA") # Exemple
    
    annees_disponibles = range(current_year - 5, current_year + 2)
    mois_disponibles = [(i, date(2000, i, 1).strftime('%B').capitalize()) for i in range(1, 13)]
    
    context = {
        'dossier': dossier,
        'page_title': _("TDB Compta - %(nom_dossier)s") % {'nom_dossier': dossier.nom_dossier},
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'label': _('TDB Comptabilité')}
        ],
        'annee_selectionnee': annee_selectionnee,
        'mois_selectionne': mois_selectionne,
        'annees_disponibles': annees_disponibles,
        'mois_disponibles': mois_disponibles,
        'premier_jour_periode': premier_jour_periode, # Ajouté pour affichage
        'kpi_nombre_comptes_plan': nombre_comptes_plan,
        'kpi_nombre_journaux_actifs': nombre_journaux_actifs,
        'kpi_nombre_tiers_actifs': nombre_tiers_actifs,
        'kpi_nombre_ecritures_periode': nombre_ecritures_periode, # Renommé pour clarté
        'kpi_total_debits_periode': total_debits_periode,       # Renommé pour clarté
        'kpi_total_credits_periode': total_credits_periode,     # Renommé pour clarté
        'kpi_solde_periode': total_debits_periode - total_credits_periode,
        'kpi_solde_tresorerie_global': solde_tresorerie,
        'kpi_prochaine_echeance_valeur': kpi_prochaine_echeance_valeur,
        'kpi_prochaine_echeance_libelle': kpi_prochaine_echeance_libelle,
        'dernieres_ecritures': dernieres_ecritures,
        'alertes_comptables': alertes_comptables,
    }
    return render(request, 'comptabilite/tableau_bord_compta.html', context)

@login_required
def plan_comptable_view(request, dossier_pk):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    comptes = CompteComptablePME.objects.filter(dossier_pme=dossier).select_related('compte_syscohada_ref', 'compte_parent').order_by('numero_compte')
    context = {
        'dossier': dossier,
        'comptes': comptes,
        'page_title': _("Plan Comptable - %(nom_dossier)s") % {'nom_dossier': dossier.nom_dossier},
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'label': _('Plan Comptable')}
        ]
    }
    return render(request, 'comptabilite/plan_comptable.html', context)

@login_required
def creer_modifier_compte_pme_view(request, dossier_pk=None, compte_pk=None):
    dossier = None
    compte_instance = None
    is_creation = True
    if compte_pk:
        compte_instance = get_object_or_404(CompteComptablePME, pk=compte_pk)
        dossier = compte_instance.dossier_pme
        is_creation = False
        page_title = _("Modifier Compte: %(num)s") % {'num': compte_instance.numero_compte}
        form_url = reverse('comptabilite:modifier_compte_pme', kwargs={'compte_pk': compte_pk})
    elif dossier_pk:
        dossier = get_object_or_404(DossierPME, pk=dossier_pk)
        page_title = _("Créer Compte Comptable")
        form_url = reverse('comptabilite:creer_compte_pme', kwargs={'dossier_pk': dossier_pk})
    else:
        messages.error(request, _("Info dossier/compte manquante."))
        return redirect('core:home')

    if request.method == 'POST':
        form = CompteComptablePMEForm(request.POST, instance=compte_instance, dossier_pme=dossier)
        if form.is_valid():
            compte_sauvegarde = form.save(commit=False)
            if is_creation:
                compte_sauvegarde.dossier_pme = dossier
            try:
                compte_sauvegarde.save()
                action_msg = _("créé") if is_creation else _("modifié")
                success_message = _("Compte '%(num)s' %(action)s.") % {'num': compte_sauvegarde.numero_compte, 'action': action_msg}
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return render(request, 'comptabilite/partials/_form_compte_pme_modal.html', {
                        'next_action': request.build_absolute_uri(reverse('comptabilite:plan_comptable', kwargs={'dossier_pk': dossier.pk}))
                    })
                messages.success(request, success_message)
                return redirect('comptabilite:plan_comptable', dossier_pk=dossier.pk)
            except IntegrityError:
                form.add_error('numero_compte', _("Ce numéro existe déjà."))
            except Exception as e:
                messages.error(request, _("Erreur: %(error)s") % {'error': e})
    else:
        form = CompteComptablePMEForm(instance=compte_instance, dossier_pme=dossier)

    breadcrumb_action_label = _("Créer Compte") if is_creation else _("Modifier %(num)s") % {'num': compte_instance.numero_compte if compte_instance else ''}
    context = {
        'form': form,
        'dossier': dossier,
        'compte_instance': compte_instance,
        'page_title': page_title,
        'page_title_modal': page_title, # Pour le modal HTMX
        'form_url': form_url,
        'is_creation': is_creation,
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'url': reverse('comptabilite:plan_comptable', kwargs={'dossier_pk': dossier.pk}), 'label': _('Plan Comptable')},
            {'label': breadcrumb_action_label}
        ]
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'comptabilite/partials/form_compte_pme.html', context) # Utiliser le partial pour HTMX
        
    return render(request, 'comptabilite/form_compte_pme_page.html', context)

@login_required
def toggle_actif_compte_pme_view(request, compte_pk):
    compte = get_object_or_404(CompteComptablePME, pk=compte_pk)
    dossier = compte.dossier_pme # Nécessaire pour la redirection
    if request.method == 'POST': 
        if compte.est_actif and LigneEcriture.objects.filter(compte_general=compte).exists():
            messages.error(request, _("Compte '%(num)s' mouvementé, désactivation impossible.") % {'num': compte.numero_compte})
            if request.htmx:
                # Retourner la ligne sans changement avec le message d'erreur
                return render(request, 'comptabilite/partials/plan_comptable_row.html', {'compte': compte, 'messages': messages.get_messages(request)})
        else:
            compte.est_actif = not compte.est_actif
            compte.save()
            action = _("activé") if compte.est_actif else _("désactivé")
            messages.success(request, _("Compte '%(num)s' %(action)s.")  % {'num': compte.numero_compte, 'action': action})
            if request.htmx:
                # Retourner la ligne mise à jour
                return render(request, 'comptabilite/partials/plan_comptable_row.html', {'compte': compte, 'messages': messages.get_messages(request)})
    else:
        messages.warning(request, _("Méthode non autorisée."))
    
    # Redirection standard si ce n'est pas une requête HTMX
    return redirect('comptabilite:plan_comptable', dossier_pk=dossier.pk)


@login_required
@transaction.atomic
def charger_plan_comptable_defaut_view(request):
    fixture_name = 'syscohada_plan.json'
    fixture_path_check = os.path.join(settings.BASE_DIR, 'comptabilite', 'fixtures', fixture_name)
    if not os.path.exists(fixture_path_check):
        messages.error(request, _("Fichier fixture '%(fixture)s' introuvable.") % {'fixture': fixture_name})
        return redirect(request.META.get('HTTP_REFERER', reverse('core:home')))
    try:
        nombre_comptes_avant = CompteComptableDefaut.objects.count()
        call_command('loaddata', fixture_name, app_label='comptabilite')
        nombre_comptes_apres = CompteComptableDefaut.objects.count()
        comptes_charges = nombre_comptes_apres - nombre_comptes_avant
        if comptes_charges > 0:
            messages.success(request, _("%(count)s comptes défaut chargés/mis à jour.") % {'count': comptes_charges})
        else:
            messages.info(request, _("Aucun nouveau compte défaut chargé."))
    except Exception as e:
        messages.error(request, _("Erreur chargement plan défaut: %(error)s") % {'error': str(e)})
    referer_url = request.META.get('HTTP_REFERER', reverse('core:home'))
    return redirect(referer_url)

@login_required
@transaction.atomic
def initialiser_plan_pme_depuis_defaut_view(request, dossier_pk):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    comptes_defaut = CompteComptableDefaut.objects.all()
    if not comptes_defaut.exists():
        messages.error(request, _("Aucun compte SYSCOHADA par défaut trouvé. Chargez-les d'abord."))
        return redirect('comptabilite:plan_comptable', dossier_pk=dossier.pk)
    
    # Utiliser la logique du signal pour la création
    # Le signal est déjà connecté et s'exécute à la création d'un DossierPME.
    # Si on veut forcer une réinitialisation, il faudrait une logique plus complexe
    # pour supprimer les comptes PME existants (avec précautions) avant de recréer.
    # Pour l'instant, on simule une "initialisation" si aucun compte PME n'existe.
    if not CompteComptablePME.objects.filter(dossier_pme=dossier).exists():
        from comptabilite.signals import creer_plan_comptable_pour_nouveau_dossier
        # Le signal s'attend à `created=True` pour un nouveau dossier.
        # Ici, on l'appelle manuellement pour un dossier existant mais sans plan.
        creer_plan_comptable_pour_nouveau_dossier(sender=DossierPME, instance=dossier, created=True)
        messages.success(request, _("Plan comptable PME initialisé à partir du plan SYSCOHADA par défaut."))
    else:
        messages.info(request, _("Le plan comptable PME existe déjà pour ce dossier."))
        
    return redirect('comptabilite:plan_comptable', dossier_pk=dossier.pk)

# --- Vues CRUD pour JournalComptable ---
@login_required
def liste_journaux_view(request, dossier_pk):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    journaux = JournalComptable.objects.filter(dossier_pme=dossier).select_related('compte_contrepartie_par_defaut').order_by('code_journal')
    context = {
        'dossier': dossier,
        'journaux': journaux,
        'page_title': _("Journaux Comptables - %(nom_dossier)s") % {'nom_dossier': dossier.nom_dossier},
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'label': _('Gestion des Journaux')},
        ]
    }
    return render(request, 'comptabilite/liste_journaux.html', context)

@login_required
@transaction.atomic
def creer_journal_view(request, dossier_pk):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    if request.method == 'POST':
        form = JournalComptableForm(request.POST, dossier_pme=dossier)
        if form.is_valid():
            journal = form.save(commit=False)
            journal.dossier_pme = dossier
            try:
                journal.save()
                messages.success(request, _("Journal '%(code)s' créé.") % {'code': journal.code_journal})
                return redirect('comptabilite:liste_journaux', dossier_pk=dossier.pk)
            except IntegrityError:
                form.add_error('code_journal', _("Code journal déjà utilisé."))
                messages.error(request, _("Code journal doit être unique."))
            except Exception as e:
                messages.error(request, _("Erreur: %(error)s") % {'error': str(e)})
    else:
        form = JournalComptableForm(dossier_pme=dossier)
    context = {
        'form': form,
        'dossier': dossier,
        'page_title': _("Créer Nouveau Journal"),
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'url': reverse('comptabilite:liste_journaux', kwargs={'dossier_pk': dossier.pk}), 'label': _('Gestion des Journaux')},
            {'label': _('Nouveau Journal')},
        ]
    }
    return render(request, 'comptabilite/form_journal.html', context)

@login_required
@transaction.atomic
def modifier_journal_view(request, journal_pk):
    journal_instance = get_object_or_404(JournalComptable, pk=journal_pk)
    dossier = journal_instance.dossier_pme
    if request.method == 'POST':
        form = JournalComptableForm(request.POST, instance=journal_instance, dossier_pme=dossier)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, _("Journal '%(code)s' modifié.") % {'code': journal_instance.code_journal})
                return redirect('comptabilite:liste_journaux', dossier_pk=dossier.pk)
            except IntegrityError:
                form.add_error('code_journal', _("Code journal déjà utilisé."))
                messages.error(request, _("Code journal doit être unique."))
            except Exception as e:
                messages.error(request, _("Erreur: %(error)s") % {'error': str(e)})
    else:
        form = JournalComptableForm(instance=journal_instance, dossier_pme=dossier)
    context = {
        'form': form,
        'dossier': dossier,
        'journal_instance': journal_instance,
        'page_title': _("Modifier Journal: %(code)s") % {'code': journal_instance.code_journal},
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'url': reverse('comptabilite:liste_journaux', kwargs={'dossier_pk': dossier.pk}), 'label': _('Gestion des Journaux')},
            {'label': _('Modifier %(code)s') % {'code': journal_instance.code_journal}},
        ]
    }
    return render(request, 'comptabilite/form_journal.html', context)

@login_required
@transaction.atomic
def supprimer_journal_view(request, journal_pk):
    journal_instance = get_object_or_404(JournalComptable, pk=journal_pk)
    dossier = journal_instance.dossier_pme
    if EcritureComptable.objects.filter(journal=journal_instance).exists():
        messages.error(request, _("Journal '%(code)s' utilisé, suppression impossible.") % {'code': journal_instance.code_journal})
        return redirect('comptabilite:liste_journaux', dossier_pk=dossier.pk)
    if request.method == 'POST':
        try:
            nom_journal = f"{journal_instance.code_journal}"
            journal_instance.delete()
            messages.success(request, _("Journal '%(nom)s' supprimé.") % {'nom': nom_journal})
        except Exception as e:
            messages.error(request, _("Erreur suppression: %(error)s") % {'error': str(e)})
        return redirect('comptabilite:liste_journaux', dossier_pk=dossier.pk)
    context = {
        'dossier': dossier,
        'journal_instance': journal_instance,
        'page_title': _("Supprimer Journal: %(code)s") % {'code': journal_instance.code_journal},
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'url': reverse('comptabilite:liste_journaux', kwargs={'dossier_pk': dossier.pk}), 'label': _('Gestion des Journaux')},
            {'label': _('Supprimer %(code)s') % {'code': journal_instance.code_journal}},
        ]
    }
    return render(request, 'comptabilite/confirm_delete_journal.html', context)

# --- Vues CRUD pour Tiers ---
@login_required
def liste_tiers_view(request, dossier_pk):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    les_tiers = Tiers.objects.filter(dossier_pme=dossier).order_by('nom_ou_raison_sociale')
    context = {
        'dossier': dossier, 
        'les_tiers': les_tiers, 
        'page_title': _("Plan Tiers - %(dossier)s") % {'dossier': dossier.nom_dossier},
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'label': _('Plan Tiers')},
        ]
    } 
    return render(request, 'comptabilite/liste_tiers.html', context) 

@login_required
@transaction.atomic
def creer_tiers_view(request, dossier_pk):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    if request.method == 'POST':
        form = TiersForm(request.POST, dossier_pme=dossier) 
        if form.is_valid():
            tiers = form.save(commit=False)
            tiers.dossier_pme = dossier
            tiers.save()
            messages.success(request, _("Tiers '%(nom)s' créé.") % {'nom': tiers.nom_ou_raison_sociale})
            return redirect('comptabilite:liste_tiers', dossier_pk=dossier.pk)
    else: 
        form = TiersForm(dossier_pme=dossier)
    context = {
        'form': form, 
        'dossier': dossier, 
        'page_title': _("Créer Nouveau Tiers"),
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'url': reverse('comptabilite:liste_tiers', kwargs={'dossier_pk': dossier.pk}), 'label': _('Plan Tiers')},
            {'label': _('Nouveau Tiers')},
        ]
    }
    return render(request, 'comptabilite/form_tiers.html', context) 

@login_required
@transaction.atomic
def modifier_tiers_view(request, tiers_pk):
    tiers_instance = get_object_or_404(Tiers, pk=tiers_pk)
    dossier = tiers_instance.dossier_pme
    if request.method == 'POST':
        form = TiersForm(request.POST, instance=tiers_instance, dossier_pme=dossier)
        if form.is_valid():
            form.save()
            messages.success(request, _("Tiers '%(nom)s' modifié.") % {'nom': tiers_instance.nom_ou_raison_sociale})
            return redirect('comptabilite:liste_tiers', dossier_pk=dossier.pk)
    else:
        form = TiersForm(instance=tiers_instance, dossier_pme=dossier)
    context = {
        'form': form,
        'dossier': dossier,
        'tiers_instance': tiers_instance,
        'page_title': _("Modifier Tiers: %(nom)s") % {'nom': tiers_instance.nom_ou_raison_sociale},
        'niveaux_breadcrumb': [
             {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'url': reverse('comptabilite:liste_tiers', kwargs={'dossier_pk': dossier.pk}), 'label': _('Plan Tiers')},
            {'label': _('Modifier %(nom)s') % {'nom': tiers_instance.nom_ou_raison_sociale[:20]}},
        ]
    }
    return render(request, 'comptabilite/form_tiers.html', context)

@login_required
@transaction.atomic
def supprimer_tiers_view(request, tiers_pk):
    tiers_instance = get_object_or_404(Tiers, pk=tiers_pk)
    dossier = tiers_instance.dossier_pme
    if LigneEcriture.objects.filter(tiers_ligne=tiers_instance).exists() or \
       EcritureComptable.objects.filter(tiers_en_tete=tiers_instance).exists():
        messages.error(request, _("Tiers '%(nom)s' utilisé dans des écritures, suppression impossible. Désactivez-le plutôt.") % {'nom': tiers_instance.nom_ou_raison_sociale})
        return redirect('comptabilite:liste_tiers', dossier_pk=dossier.pk)
    
    if request.method == 'POST':
        nom_tiers = tiers_instance.nom_ou_raison_sociale
        tiers_instance.delete()
        messages.success(request, _("Tiers '%(nom)s' supprimé.") % {'nom': nom_tiers})
        return redirect('comptabilite:liste_tiers', dossier_pk=dossier.pk)
        
    context = {
        'dossier': dossier,
        'tiers_instance': tiers_instance,
        'page_title': _("Supprimer Tiers: %(nom)s") % {'nom': tiers_instance.nom_ou_raison_sociale},
         'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'url': reverse('comptabilite:liste_tiers', kwargs={'dossier_pk': dossier.pk}), 'label': _('Plan Tiers')},
            {'label': _('Supprimer %(nom)s') % {'nom': tiers_instance.nom_ou_raison_sociale[:20]}},
        ]
    }
    return render(request, 'comptabilite/confirm_delete_tiers.html', context)

# --- Vues CRUD pour TauxDeTaxe ---
@login_required
def liste_taux_taxes_view(request, dossier_pk):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    taux_taxes = TauxDeTaxe.objects.filter(dossier_pme=dossier).select_related('compte_de_taxe').order_by('code_taxe')
    context = {
        'dossier': dossier, 
        'taux_taxes': taux_taxes, 
        'page_title': _("Taux de Taxes - %(dossier)s") % {'dossier': dossier.nom_dossier},
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'label': _('Taux de Taxes')},
        ]
    }
    return render(request, 'comptabilite/liste_taux_taxes.html', context) 

@login_required
@transaction.atomic
def creer_taux_taxe_view(request, dossier_pk):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    if request.method == 'POST':
        form = TauxDeTaxeForm(request.POST, dossier_pme=dossier)
        if form.is_valid():
            taxe = form.save(commit=False)
            taxe.dossier_pme = dossier
            taxe.save()
            messages.success(request, _("Taux de taxe '%(code)s' créé.") % {'code': taxe.code_taxe})
            return redirect('comptabilite:liste_taux_taxes', dossier_pk=dossier.pk)
    else: 
        form = TauxDeTaxeForm(dossier_pme=dossier)
    context = {
        'form': form, 
        'dossier': dossier, 
        'page_title': _("Créer Taux de Taxe"),
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'url': reverse('comptabilite:liste_taux_taxes', kwargs={'dossier_pk': dossier.pk}), 'label': _('Taux de Taxes')},
            {'label': _('Nouveau Taux')},
        ]
    }
    return render(request, 'comptabilite/form_taux_taxe.html', context) 

@login_required
@transaction.atomic
def modifier_taux_taxe_view(request, taux_pk):
    taxe_instance = get_object_or_404(TauxDeTaxe, pk=taux_pk)
    dossier = taxe_instance.dossier_pme
    if request.method == 'POST':
        form = TauxDeTaxeForm(request.POST, instance=taxe_instance, dossier_pme=dossier)
        if form.is_valid():
            form.save()
            messages.success(request, _("Taux de taxe '%(code)s' modifié.") % {'code': taxe_instance.code_taxe})
            return redirect('comptabilite:liste_taux_taxes', dossier_pk=dossier.pk)
    else:
        form = TauxDeTaxeForm(instance=taxe_instance, dossier_pme=dossier)
    context = {
        'form': form,
        'dossier': dossier,
        'taxe_instance': taxe_instance,
        'page_title': _("Modifier Taux: %(code)s") % {'code': taxe_instance.code_taxe},
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'url': reverse('comptabilite:liste_taux_taxes', kwargs={'dossier_pk': dossier.pk}), 'label': _('Taux de Taxes')},
            {'label': _('Modifier %(code)s') % {'code': taxe_instance.code_taxe}},
        ]
    }
    return render(request, 'comptabilite/form_taux_taxe.html', context)

@login_required
@transaction.atomic
def supprimer_taux_taxe_view(request, taux_pk):
    taxe_instance = get_object_or_404(TauxDeTaxe, pk=taux_pk)
    dossier = taxe_instance.dossier_pme
    # TODO: Vérifier si le taux est utilisé avant suppression
    if request.method == 'POST':
        code_taxe = taxe_instance.code_taxe
        taxe_instance.delete()
        messages.success(request, _("Taux de taxe '%(code)s' supprimé.") % {'code': code_taxe})
        return redirect('comptabilite:liste_taux_taxes', dossier_pk=dossier.pk)
    context = {
        'dossier': dossier,
        'taxe_instance': taxe_instance,
        'page_title': _("Supprimer Taux: %(code)s") % {'code': taxe_instance.code_taxe},
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'url': reverse('comptabilite:liste_taux_taxes', kwargs={'dossier_pk': dossier.pk}), 'label': _('Taux de Taxes')},
            {'label': _('Supprimer %(code)s') % {'code': taxe_instance.code_taxe}},
        ]
    }
    return render(request, 'comptabilite/confirm_delete_taux_taxe.html', context)

# --- Vues pour la Saisie des Pièces Comptables (avec logique HTMX) ---
@login_required
def saisie_selection_journal_periode_view(request, dossier_pk):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    if request.method == 'POST':
        form = SaisieJournalSelectionForm(request.POST, dossier_pme=dossier)
        if form.is_valid():
            journal_obj = form.cleaned_data['journal']
            annee_saisie = form.cleaned_data['annee']
            mois_saisie = form.cleaned_data['mois'] 
            return redirect('comptabilite:saisie_piece', dossier_pk=dossier.pk, journal_pk=journal_obj.pk, annee=annee_saisie, mois=mois_saisie)
        else:
            messages.error(request, _("Veuillez corriger les erreurs de sélection."))
    else:
        form = SaisieJournalSelectionForm(dossier_pme=dossier)
    context = {
        'dossier': dossier,
        'form': form,
        'page_title': _("Saisie - Sélection Journal & Période"),
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'label': _("Sélection Journal & Période")}
        ]
    }
    return render(request, 'comptabilite/saisie_selection_journal_periode.html', context)

@login_required
@transaction.atomic 
def saisie_piece_view(request, dossier_pk, journal_pk, annee, mois):
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    journal_obj = get_object_or_404(JournalComptable, pk=journal_pk, dossier_pme=dossier)
    try:
        annee_saisie = int(annee)
        mois_saisie = int(mois)
        date_ecriture_default_entete = date(annee_saisie, mois_saisie, 1) 
        if not (1 <= mois_saisie <= 12 and 1900 <= annee_saisie <= date.today().year + 10):
            raise ValueError(_("Période invalide."))
    except ValueError as e: 
        messages.error(request, str(e))
        return redirect('comptabilite:saisie_selection_journal_periode', dossier_pk=dossier.pk)

    comptes_pme_actifs = CompteComptablePME.objects.filter(
        dossier_pme=dossier, est_actif=True
    ).values('pk', 'numero_compte', 'intitule_compte') # Ajout de 'pk'
    comptes_pme_json = json.dumps(list(comptes_pme_actifs), cls=DjangoJSONEncoder)

    tiers_pme_actifs = Tiers.objects.filter(
        dossier_pme=dossier, est_actif=True
    ).values('pk', 'code_tiers', 'nom_ou_raison_sociale') # Ajout de 'pk'
    tiers_pme_json = json.dumps(list(tiers_pme_actifs), cls=DjangoJSONEncoder)
    
    numero_piece_conteneur = get_next_numero_piece(journal_obj, annee_saisie, mois_saisie)
    libelle_piece_conteneur = f"Saisie Journal {journal_obj.code_journal} - {mois_saisie:02d}/{annee_saisie}"

    ecriture_conteneur, created_conteneur = EcritureComptable.objects.get_or_create(
        dossier_pme=dossier,
        journal=journal_obj,
        numero_piece=numero_piece_conteneur,
        date_ecriture__year=annee_saisie,
        date_ecriture__month=mois_saisie,
        defaults={
            'date_ecriture': date_ecriture_default_entete,
            'libelle_piece': libelle_piece_conteneur,
        }
    )
    if not created_conteneur and (ecriture_conteneur.date_ecriture.year != annee_saisie or ecriture_conteneur.date_ecriture.month != mois_saisie):
        ecriture_conteneur.date_ecriture = date_ecriture_default_entete
        ecriture_conteneur.libelle_piece = libelle_piece_conteneur
        ecriture_conteneur.save()

    form_en_tete_kwargs = {'dossier_pme': dossier, 'journal': journal_obj, 'prefix': 'en_tete'}
    formset_lignes_kwargs = {'prefix': 'lignes', 'form_kwargs': {'dossier_pme': dossier}}

    if request.method == 'POST':
        # Le formulaire d'en-tête est lié à l'ecriture_conteneur pour initialisation,
        # mais ses données sont destinées aux lignes.
        form_en_tete = PieceComptableEnTeteForm(request.POST, instance=ecriture_conteneur, **form_en_tete_kwargs)
        formset_lignes = LigneEcritureSaisieFormSet(request.POST, instance=ecriture_conteneur, **formset_lignes_kwargs)
        
        if form_en_tete.is_valid() and formset_lignes.is_valid():
            try:
                with transaction.atomic():
                    # L'instance ecriture_conteneur est déjà prête.
                    # Les données de form_en_tete servent de valeurs par défaut pour les lignes.
                    jour_entete = form_en_tete.cleaned_data.get('jour')
                    num_piece_entete = form_en_tete.cleaned_data.get('numero_piece')
                    num_facture_entete = form_en_tete.cleaned_data.get('numero_facture_liee')
                    ref_entete = form_en_tete.cleaned_data.get('reference_piece')
                    libelle_entete = form_en_tete.cleaned_data.get('libelle_piece')
                    tiers_entete = form_en_tete.cleaned_data.get('tiers_en_tete')
                    
                    formset_lignes.instance = ecriture_conteneur # S'assurer que le formset est lié au bon conteneur
                    lignes_sauvegardees = formset_lignes.save(commit=False)
                    
                    for ligne in lignes_sauvegardees:
                        if not ligne.jour and jour_entete: ligne.jour = jour_entete
                        if not ligne.numero_piece and num_piece_entete: ligne.numero_piece = num_piece_entete
                        if not ligne.numero_facture and num_facture_entete: ligne.numero_facture = num_facture_entete
                        if not ligne.reference and ref_entete: ligne.reference = ref_entete
                        if not ligne.libelle_ligne and libelle_entete: ligne.libelle_ligne = libelle_entete
                        if not ligne.tiers_ligne and tiers_entete and ligne.compte_general and \
                           ligne.compte_general.type_compte in ['TIERS_CLIENT', 'TIERS_FOURNISSEUR', 'TIERS_SALARIE']:
                            ligne.tiers_ligne = tiers_entete
                        
                        ligne.ecriture = ecriture_conteneur # Assurer la liaison explicite
                        ligne.save()
                    formset_lignes.save_m2m()
                    
                messages.success(request, _("Lignes d'écriture enregistrées dans le journal."))
                return redirect('comptabilite:saisie_piece', 
                             dossier_pk=dossier.pk, journal_pk=journal_obj.pk,
                             annee=annee_saisie, mois=mois_saisie)
            except Exception as e:
                messages.error(request, _("Erreur lors de la sauvegarde : %(error)s") % {'error': str(e)})
    else:
        # En GET, initialiser le form_en_tete avec des valeurs par défaut pour la saisie
        # L'instance ecriture_conteneur est utilisée pour le formset pour charger les lignes existantes.
        form_en_tete = PieceComptableEnTeteForm(
            initial={'jour': date.today().day}, # Jour par défaut pour la nouvelle saisie
            dossier_pme=dossier, journal=journal_obj, prefix='en_tete'
        )
        formset_lignes = LigneEcritureSaisieFormSet(instance=ecriture_conteneur, **formset_lignes_kwargs)

    # Calcul des totaux en utilisant les agrégations sur les lignes existantes
    totaux_agg = ecriture_conteneur.lignes_ecriture.aggregate(
        total_debit=Coalesce(Sum('debit'), Value(Decimal('0.00'))),
        total_credit=Coalesce(Sum('credit'), Value(Decimal('0.00')))
    )
    totaux = {
        'total_debit': totaux_agg['total_debit'],
        'total_credit': totaux_agg['total_credit'],
        'solde': totaux_agg['total_debit'] - totaux_agg['total_credit']
    }

    context = {
        'dossier': dossier,
        'journal': journal_obj,
        'form_en_tete': form_en_tete,
        'formset_lignes': formset_lignes,
        'totaux': totaux,
        'annee_saisie': annee_saisie,
        'mois_saisie': mois_saisie,
        'page_title': _("Saisie Journal: %(code)s (%(mois)02d/%(annee)s)") % {
            'code': journal_obj.code_journal, 'mois': mois_saisie, 'annee': annee_saisie
        },
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'label': _("Saisie Journal %(code)s") % {'code': journal_obj.code_journal}}
        ],
        'comptes_pme_json': comptes_pme_json,
        'tiers_pme_json': tiers_pme_json,
        'lignes_existantes_json': json.dumps([]), # Le formset gère les lignes existantes
        # Passer les IDs pour AJAX
        'current_dossier_pk': dossier.pk,
        'current_journal_pk': journal_obj.pk,
        'current_annee_saisie': annee_saisie,
        'current_mois_saisie': mois_saisie,
    }
    
    if request.htmx:
        action = request.GET.get('action')
        if action == 'ajouter_ligne':
            # Pour HTMX, on veut ajouter une nouvelle forme vide au formset
            # Le template _saisie_ligne_form.html doit être adapté pour rendre un form du formset
            # et non des inputs HTML simples.
            # La logique actuelle de htmx_ajouter_ligne_ecriture_view est plus adaptée.
            # Ici, on pourrait retourner le formset entier ou juste la nouvelle forme.
            # Pour l'instant, on laisse la logique HTMX séparée.
            # return render(request, 'comptabilite/partials/_saisie_ligne_form.html', context) # Exemple
            pass 
        elif action == 'recalculer_totaux':
            # La vue htmx_recalculer_totaux_view est dédiée à cela.
            # return render(request, 'comptabilite/partials/_saisie_totaux.html', {'totaux': totaux})
            pass
            
    return render(request, 'comptabilite/saisie_piece_form.html', context)


@login_required
def htmx_recalculer_totaux_view(request, dossier_pk, journal_pk, annee, mois):
    if not request.htmx:
        return HttpResponseBadRequest("Requête HTMX attendue.")
        
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    # L'instance EcritureComptable n'est pas cruciale ici car on recalcule sur la base des données POSTées
    # qui représentent l'état du formulaire côté client.
    ecriture_instance = EcritureComptable() 
    formset_lignes_kwargs = {'prefix': 'lignes', 'form_kwargs': {'dossier_pme': dossier}}
    
    formset = LigneEcritureSaisieFormSet(request.POST or None, instance=ecriture_instance, **formset_lignes_kwargs)
    
    # Il faut appeler is_valid() pour peupler cleaned_data. 
    # Les erreurs de validation des lignes individuelles seront dans form.errors.
    # L'erreur d'équilibre du formset sera dans formset.non_form_errors().
    formset.is_valid() # Appel pour la validation et cleaned_data

    totaux = {'total_debit': Decimal(0), 'total_credit': Decimal(0), 'solde': Decimal(0)}
    for form_ligne in formset.forms:
        is_deleted = False
        if form_ligne.prefix + '-DELETE' in request.POST and request.POST[form_ligne.prefix + '-DELETE']:
            is_deleted = True

        if not is_deleted:
            debit = Decimal(0)
            credit = Decimal(0)
            # Utiliser cleaned_data si la ligne est valide, sinon parser les données brutes
            if hasattr(form_ligne, 'cleaned_data') and form_ligne.cleaned_data:
                debit = form_ligne.cleaned_data.get('debit') or Decimal(0)
                credit = form_ligne.cleaned_data.get('credit') or Decimal(0)
            elif form_ligne.is_bound and form_ligne.data: 
                try: 
                    debit_str = form_ligne.data.get(form_ligne.prefix + '-debit', '0') or '0'
                    debit = Decimal(debit_str.replace(',', '.'))
                except: pass
                try: 
                    credit_str = form_ligne.data.get(form_ligne.prefix + '-credit', '0') or '0'
                    credit = Decimal(credit_str.replace(',', '.'))
                except: pass
            
            totaux['total_debit'] += debit
            totaux['total_credit'] += credit
            
    totaux['solde'] = totaux['total_debit'] - totaux['total_credit']
    
    context = {'totaux': totaux}
    # Le template _saisie_totaux.html est utilisé par la grille Sage,
    # pour le formulaire standard, il faudrait un partial différent ou adapter celui-ci.
    # Pour l'instant, on suppose que le JS de saisie_piece_form.html gère l'affichage des totaux.
    # Si on veut que HTMX mette à jour les totaux, il faut un partial pour cela.
    # Exemple: return render(request, 'comptabilite/partials/_standard_saisie_totaux.html', context)
    return JsonResponse(totaux) # Ou un partial HTML si le JS ne le fait pas

@login_required
def htmx_ajouter_ligne_ecriture_view(request, dossier_pk, journal_pk, annee, mois):
    if not request.htmx:
        return HttpResponseBadRequest("Requête HTMX attendue.")

    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    journal_obj = get_object_or_404(JournalComptable, pk=journal_pk, dossier_pme=dossier)
    annee_saisie = int(annee)
    mois_saisie = int(mois)

    # Créer une instance vide d'EcritureComptable juste pour le formset
    # Elle ne sera pas sauvegardée ici.
    ecriture_instance = EcritureComptable(
        dossier_pme=dossier, 
        journal=journal_obj, 
        date_ecriture=date(annee_saisie, mois_saisie, 1)
    )
    
    formset_lignes_kwargs = {'prefix': 'lignes', 'form_kwargs': {'dossier_pme': dossier}}
    
    # Copier les données POST pour manipuler TOTAL_FORMS
    form_data = request.POST.copy() if request.POST else {}
    prefix = LigneEcritureSaisieFormSet.get_default_prefix() # Ou 'lignes' si vous l'avez défini
    
    # Incrémenter TOTAL_FORMS
    total_forms_key = f'{prefix}-TOTAL_FORMS'
    current_total_forms = int(form_data.get(total_forms_key, 0))
    form_data[total_forms_key] = str(current_total_forms + 1)
    
    # Initialiser le formset avec les données modifiées (pour inclure la nouvelle forme vide)
    formset_avec_extra = LigneEcritureSaisieFormSet(form_data, instance=ecriture_instance, **formset_lignes_kwargs)
    
    # Rendre seulement la nouvelle forme (la dernière)
    nouvelle_forme = formset_avec_extra.forms[-1]
    
    context_partial = {
        'form_ligne': nouvelle_forme, # Passer la nouvelle forme au template partiel
        'formset': formset_avec_extra, # Le formset entier peut être utile pour les IDs, etc.
        'dossier': dossier, 
        'journal': journal_obj,
        'annee_saisie': annee_saisie, 
        'mois_saisie': mois_saisie
    }
    
    # Utiliser un template partiel qui rend une seule ligne de formulaire
    # Ce template doit être compatible avec la structure attendue par votre JS
    # ou par la soumission de formulaire standard.
    # Le template _saisie_ligne_form.html est pour la grille Sage.
    # Il faut un template pour la ligne du formset standard.
    # Exemple: 'comptabilite/partials/_formset_ligne_standard.html'
    
    # Pour l'instant, si le JS de saisie_piece_form.html ajoute les lignes manuellement,
    # cette vue HTMX n'est pas directement utilisée par ce template.
    # Elle serait utilisée si le tableau était géré par des échanges HTMX.
    
    # Si le JS de saisie_piece_form.html s'attend à un fragment HTML pour une nouvelle ligne:
    # html_response = render_to_string('comptabilite/partials/_formset_ligne_standard.html', context_partial, request=request)
    # response = HttpResponse(html_response)
    # response['HX-Trigger'] = json.dumps({'LigneAjoutee': True, 'updateTotals': True}) # Pour que le JS mette à jour les totaux
    # return response

    # Si le JS gère tout, cette vue n'est pas appelée par saisie_piece_form.html pour ajouter une ligne.
    # Elle est plus pertinente pour une grille entièrement gérée par HTMX.
    return HttpResponse("Logique HTMX pour ajouter une ligne au formset standard à implémenter si nécessaire.")


@login_required
@require_POST # S'assurer que c'est une requête POST
@transaction.atomic
def enregistrer_ligne_ajax_view(request, dossier_pk, journal_pk, annee, mois):
    try:
        dossier = get_object_or_404(DossierPME, pk=dossier_pk)
        journal_obj = get_object_or_404(JournalComptable, pk=journal_pk, dossier_pme=dossier)
        
        try:
            annee_saisie = int(annee)
            mois_saisie = int(mois)
            date_ecriture_default_entete = date(annee_saisie, mois_saisie, 1)
            if not (1 <= mois_saisie <= 12 and 1900 <= annee_saisie <= date.today().year + 10):
                raise ValueError(_("Période invalide."))
        except ValueError as e_period:
            logger.warning(f"Invalid period in enregistrer_ligne_ajax_view: {e_period} for dossier {dossier_pk}, journal {journal_pk}")
            return JsonResponse({'success': False, 'errors': {'__all__': [str(e_period)]}}, status=400)

        # Récupérer ou créer l'EcritureComptable "conteneur"
        numero_piece_conteneur = get_next_numero_piece(journal_obj, annee_saisie, mois_saisie)
        libelle_piece_conteneur = f"Saisie Journal {journal_obj.code_journal} - {mois_saisie:02d}/{annee_saisie}"
        ecriture_conteneur, __ = EcritureComptable.objects.get_or_create(
            dossier_pme=dossier,
            journal=journal_obj,
            numero_piece=numero_piece_conteneur,
            date_ecriture__year=annee_saisie,
            date_ecriture__month=mois_saisie,
            defaults={
                'date_ecriture': date_ecriture_default_entete,
                'libelle_piece': libelle_piece_conteneur,
            }
        )

        try:
            data = json.loads(request.body)
            logger.debug(f"Received data for enregistrer_ligne_ajax_view (dossier {dossier_pk}, journal {journal_pk}): {data}")
        except json.JSONDecodeError as e_json:
            logger.warning(f"JSONDecodeError in enregistrer_ligne_ajax_view (dossier {dossier_pk}, journal {journal_pk}): {e_json} - Body: {request.body[:200]}")
            return JsonResponse({'success': False, 'errors': {'__all__': [_("Données JSON invalides.")]}}, status=400)

        # Utiliser un formulaire pour valider les données de la ligne
        form_ligne_data = {
            'jour': data.get('jour'),
            'numero_piece': data.get('numero_piece'),
            'numero_facture': data.get('numero_facture'),
            'reference': data.get('reference'),
            'compte_general': data.get('compte_general'), # Doit être l'ID du compte
            'tiers_ligne': data.get('tiers_ligne'),       # Doit être l'ID du tiers
            'libelle_ligne': data.get('libelle_ligne'),
            'date_echeance_ligne': data.get('date_echeance_ligne') or None,
            'debit': data.get('debit', '0.00'), # Garder en string pour le formulaire, qui convertira
            'credit': data.get('credit', '0.00'),# Idem
        }
        
        form = LigneEcritureSaisieForm(form_ligne_data, dossier_pme=dossier)

        if form.is_valid():
            ligne = form.save(commit=False)
            ligne.ecriture = ecriture_conteneur # Assurer la liaison explicite
            
            # Déterminer le prochain ordre pour la ligne
            max_ordre = LigneEcriture.objects.filter(ecriture=ecriture_conteneur).aggregate(Max('ordre'))['ordre__max']
            ligne.ordre = (max_ordre if max_ordre is not None else -1) + 1
            
            ligne.save()
            
            # Recalculer les totaux après la sauvegarde
            totaux_agg = ecriture_conteneur.lignes_ecriture.aggregate(
                total_debit=Coalesce(Sum('debit'), Value(Decimal('0.00'))),
                total_credit=Coalesce(Sum('credit'), Value(Decimal('0.00')))
            )
            
            # Préparer les données de la ligne pour la réponse JSON
            ligne_data = {
                'id': ligne.pk,
                'ordre': ligne.ordre,
                'compte_general_id': ligne.compte_general.pk,
                'compte_general_numero': ligne.compte_general.numero_compte,
                'compte_general_intitule': ligne.compte_general.intitule_compte,
                'tiers_ligne_id': ligne.tiers_ligne.pk if ligne.tiers_ligne else None,
                'tiers_ligne_code': ligne.tiers_ligne.code_tiers if ligne.tiers_ligne else None,
                'tiers_ligne_nom': ligne.tiers_ligne.nom_ou_raison_sociale if ligne.tiers_ligne else None,
                'libelle_ligne': ligne.libelle_ligne,
                'date_echeance_ligne': ligne.date_echeance_ligne.strftime('%Y-%m-%d') if ligne.date_echeance_ligne else None,
                'debit': str(ligne.debit),
                'credit': str(ligne.credit),
                'jour': ligne.jour,
                'numero_piece': ligne.numero_piece,
                'numero_facture': ligne.numero_facture,
                'reference': ligne.reference,
            }
            
            return JsonResponse({
                'success': True,
                'message': _("Ligne enregistrée avec succès."),
                'ligne': ligne_data,
                'totaux': {
                    'total_debit': str(totaux_agg['total_debit']),
                    'total_credit': str(totaux_agg['total_credit']),
                    'solde': str(totaux_agg['total_debit'] - totaux_agg['total_credit']),
                }
            })
        else:
            logger.warning(f"Form errors in enregistrer_ligne_ajax_view (dossier {dossier_pk}, journal {journal_pk}): {form.errors.as_json()}")
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    except Exception as e:
        logger.exception(f"Unhandled exception in enregistrer_ligne_ajax_view (dossier {dossier_pk}, journal {journal_pk})")
        return JsonResponse({'success': False, 'errors': {'__all__': [str(e)]}}, status=500)
            ligne.ecriture = ecriture_conteneur # Assurer la liaison explicite
            
            # Déterminer le prochain ordre pour la ligne
            max_ordre = LigneEcriture.objects.filter(ecriture=ecriture_conteneur).aggregate(Max('ordre'))['ordre__max']
            ligne.ordre = (max_ordre if max_ordre is not None else -1) + 1
            
            ligne.save()
            
            # Recalculer les totaux après la sauvegarde
            totaux_agg = ecriture_conteneur.lignes_ecriture.aggregate(
                total_debit=Coalesce(Sum('debit'), Value(Decimal('0.00'))),
                total_credit=Coalesce(Sum('credit'), Value(Decimal('0.00')))
            )
            
            # Préparer les données de la ligne pour la réponse JSON
            ligne_data = {
                'id': ligne.pk,
                'ordre': ligne.ordre,
                'compte_general_id': ligne.compte_general.pk,
                'compte_general_numero': ligne.compte_general.numero_compte,
                'compte_general_intitule': ligne.compte_general.intitule_compte,
                'tiers_ligne_id': ligne.tiers_ligne.pk if ligne.tiers_ligne else None,
                'tiers_ligne_code': ligne.tiers_ligne.code_tiers if ligne.tiers_ligne else None,
                'tiers_ligne_nom': ligne.tiers_ligne.nom_ou_raison_sociale if ligne.tiers_ligne else None,
                'libelle_ligne': ligne.libelle_ligne,
                'date_echeance_ligne': ligne.date_echeance_ligne.strftime('%Y-%m-%d') if ligne.date_echeance_ligne else None,
                'debit': str(ligne.debit),
                'credit': str(ligne.credit),
                'jour': ligne.jour,
                'numero_piece': ligne.numero_piece,
                'numero_facture': ligne.numero_facture,
                'reference': ligne.reference,
            }
            
            return JsonResponse({
                'success': True,
                'message': _("Ligne enregistrée avec succès."),
                'ligne': ligne_data,
                'totaux': {
                    'total_debit': str(totaux_agg['total_debit']),
                    'total_credit': str(totaux_agg['total_credit']),
                    'solde': str(totaux_agg['total_debit'] - totaux_agg['total_credit']),
                }
            })
        else:
            logger.warning(f"Form errors in enregistrer_ligne_ajax_view (dossier {dossier_pk}, journal {journal_pk}): {form.errors.as_json()}")
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    except Exception as e:
        logger.exception(f"Unhandled exception in enregistrer_ligne_ajax_view (dossier {dossier_pk}, journal {journal_pk})")
        return JsonResponse({'success': False, 'errors': {'__all__': [str(e)]}}, status=500)

