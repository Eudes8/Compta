"""
Views for handling the Sage Grid interface for accounting entries.
"""
from typing import Dict, Any, List
import json
from datetime import date, datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.db.models import Q

from dossiers_pme.models import DossierPME
from comptabilite.models import (
    JournalComptable,
    EcritureComptable,
    LigneEcriture,
    CompteComptablePME,
    Tiers
)
from comptabilite.utils.sage_grid_handler import (
    SageGridHandler,
    process_sage_grid_data,
    search_accounts
)


@login_required
def saisie_sage_grid_view(request, dossier_pk, journal_pk, annee, mois):
    """
    View for the Sage Grid entry interface.
    """
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    journal = get_object_or_404(JournalComptable, pk=journal_pk, dossier_pme=dossier)
    
    try:
        annee_saisie = int(annee)
        mois_saisie = int(mois)
        if not (1 <= mois_saisie <= 12):
            raise ValueError("Invalid month")
    except ValueError:
        messages.error(request, _("Invalid period parameters"))
        return redirect('comptabilite:saisie_selection_journal_periode', dossier_pk=dossier_pk)
    
    # Create a date for the entry
    date_ecriture = date(annee_saisie, mois_saisie, 1)
    
    # Initialize handler for formatting and validation
    grid_handler = SageGridHandler(dossier, journal, date_ecriture)
    
    # Prepare initial grid data with 10 empty rows
    initial_grid_data = []
    
    # Check if there's a suggested piece number for this journal and period
    from comptabilite.views import get_next_numero_piece
    suggested_piece_number = get_next_numero_piece(journal, annee_saisie, mois_saisie)
    
    context = {
        'dossier': dossier,
        'journal': journal,
        'annee_saisie': annee_saisie,
        'mois_saisie': mois_saisie,
        'suggested_piece_number': suggested_piece_number,
        'grid_data': initial_grid_data,
        'page_title': _("Journal: %(code)s - Sage 100") % {'code': journal.code_journal},
        'hide_header': True,  # Masquer l'en-tête pour l'interface Sage
        'hide_footer': True,  # Masquer le pied de page pour l'interface Sage
        'niveaux_breadcrumb': [
            {'url': reverse('core:home'), 'label': _('TDB Global')},
            {'url': reverse('dossiers_pme:detail_dossier', kwargs={'pk': dossier.pk}), 'label': dossier.nom_dossier},
            {'url': reverse('comptabilite:tableau_bord_compta', kwargs={'dossier_pk': dossier.pk}), 'label': _('Comptabilité')},
            {'label': _("Saisie - %(code)s") % {'code': journal.code_journal}}
        ]
    }
    
    return render(request, 'comptabilite/saisie_piece_form.html', context)


@login_required
@require_POST
def save_sage_grid_entry(request, dossier_pk, journal_pk, annee, mois):
    """
    API endpoint to save a Sage Grid accounting entry.
    """
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    journal = get_object_or_404(JournalComptable, pk=journal_pk, dossier_pme=dossier)
    
    try:
        date_ecriture = date(int(annee), int(mois), 1)
    except ValueError:
        return JsonResponse({'success': False, 'errors': ['Invalid date parameters']})
    
    return process_sage_grid_data(request, dossier, journal, date_ecriture)


@login_required
def search_accounts_view(request, dossier_pk):
    """
    API endpoint to search for accounts in a dossier.
    """
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'results': []})
        
    accounts = search_accounts(dossier, query)
    results = [{
        'id': account.numero_compte,
        'text': f"{account.numero_compte} - {account.intitule_compte}",
        'numero': account.numero_compte,
        'intitule': account.intitule_compte,
        'type': account.type_compte
    } for account in accounts]
    
    return JsonResponse({'results': results})


@login_required
def search_tiers_view(request, dossier_pk):
    """
    API endpoint to search for tiers (customers/vendors).
    """
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'results': []})
    
    # Search by tiers code or name
    tiers_list = Tiers.objects.filter(
        dossier_pme=dossier,
        est_actif=True
    ).filter(
        Q(code_tiers__icontains=query) | 
        Q(nom_ou_raison_sociale__icontains=query)
    ).order_by('code_tiers')[:20]
    
    results = [{
        'code': tiers.code_tiers,
        'nom': tiers.nom_ou_raison_sociale,
        'type': tiers.get_type_tiers_display()
    } for tiers in tiers_list]
    
    return JsonResponse({'results': results})


@login_required
def get_piece_data(request, piece_pk):
    """
    API endpoint to retrieve data for an existing accounting entry.
    """
    piece = get_object_or_404(EcritureComptable, pk=piece_pk)
    
    # Check permissions
    if request.user.dossier_pme != piece.dossier_pme:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Format header data
    header_data = {
        'journal': piece.journal.code_journal,
        'date_ecriture': piece.date_ecriture.strftime('%d/%m/%Y'),
        'numero_piece': piece.numero_piece,
        'libelle_piece': piece.libelle_piece,
        'numero_facture': piece.numero_facture_liee,
        'reference': piece.reference_piece,
        'tiers_en_tete': piece.tiers_en_tete.code_tiers if piece.tiers_en_tete else '',
        'date_echeance': piece.date_echeance_piece.strftime('%d/%m/%Y') if piece.date_echeance_piece else '',
    }
    
    # Format grid data
    grid_handler = SageGridHandler(piece.dossier_pme)
    grid_data = []
    
    for ligne in piece.lignes_ecriture.all().order_by('ordre'):
        row_data = {
            'jour': ligne.jour,
            'piece': ligne.numero_piece or piece.numero_piece,
            'facture': ligne.numero_facture or piece.numero_facture_liee,
            'ref': ligne.reference or piece.reference_piece,
            'compte': ligne.compte_general.numero_compte,
            'tiers': ligne.tiers_ligne.code_tiers if ligne.tiers_ligne else '',
            'libelle': ligne.libelle_ligne,
            'echeance': ligne.date_echeance_ligne.strftime('%d/%m/%Y') if ligne.date_echeance_ligne else '',
            'lettrage': ligne.lettrage_code or '',
            'debit': grid_handler.format_monetary_value(ligne.debit) if ligne.debit else '',
            'credit': grid_handler.format_monetary_value(ligne.credit) if ligne.credit else '',
        }
        grid_data.append(row_data)
    
    return JsonResponse({
        'success': True,
        'header': header_data,
        'grid': grid_data
    })


@login_required
def saisie_interactive_view(request, dossier_pk):
    """Vue pour la saisie interactive des écritures comptables style Sage"""
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    
    # Récupérer tous les journaux actifs du dossier
    journaux = JournalComptable.objects.filter(
        dossier_pme=dossier,
        est_actif=True
    ).order_by('code_journal')
    
    context = {
        'dossier': dossier,
        'journaux': journaux,
        'page_title': _('Saisie Interactive - %(dossier)s') % {'dossier': dossier.nom_dossier}
    }
    
    return render(request, 'comptabilite/saisie_interactive.html', context)

@login_required
def comptes_lookup(request):
    """API pour la recherche de comptes"""
    dossier_pk = request.GET.get('dossier_pk')
    query = request.GET.get('query', '').strip()
    journal_type = request.GET.get('journal_type', '')
    
    # Filtres de base
    base_filters = Q(
        dossier_pme_id=dossier_pk,
        est_actif=True,
        # nature_compte='DETAIL' # Permettre tous les types de comptes actifs
    )
    
    # Filtres spécifiques selon le type de journal
    if journal_type == 'AC':
        # Pour les achats: comptes fournisseurs et charges
        compte_filters = Q(numero_compte__startswith='401') | Q(numero_compte__startswith='60') | Q(numero_compte__startswith='44566')
    elif journal_type == 'VE':
        # Pour les ventes: comptes clients et produits
        compte_filters = Q(numero_compte__startswith='411') | Q(numero_compte__startswith='70') | Q(numero_compte__startswith='44571')
    elif journal_type in ['BQ', 'CA']:
        # Pour banque et caisse: tous les comptes sauf trésorerie
        compte_filters = ~Q(type_compte__in=['TRESORERIE_ACTIF', 'TRESORERIE_PASSIF'])
    else:
        # Pour les OD: tous les comptes de détail
        compte_filters = Q()
    
    # Recherche
    if query:
        search_filter = Q(numero_compte__icontains=query) | Q(intitule_compte__icontains=query)
        comptes = CompteComptablePME.objects.filter(base_filters & compte_filters & search_filter)
    else:
        comptes = CompteComptablePME.objects.filter(base_filters & compte_filters)
    
    comptes = comptes.order_by('numero_compte')[:50]
    
    return JsonResponse({
        'results': [{
            'numero': compte.numero_compte,
            'libelle': compte.intitule_compte,
            'type': compte.type_compte,
            'est_lettrable': compte.est_lettrable
        } for compte in comptes]
    })

@login_required
def tiers_lookup(request):
    """API pour la recherche de tiers"""
    dossier_pk = request.GET.get('dossier_pk')
    query = request.GET.get('query', '').strip()
    journal_type = request.GET.get('journal_type', '')
    
    # Filtres de base
    base_filters = Q(
        dossier_pme_id=dossier_pk,
        est_actif=True
    )
    
    # Filtres spécifiques selon le type de journal
    if journal_type == 'AC':
        tiers_filters = Q(type_tiers='FO')  # Fournisseurs
    elif journal_type == 'VE':
        tiers_filters = Q(type_tiers='CL')  # Clients
    else:
        tiers_filters = Q()  # Tous les tiers
    
    # Recherche
    if query:
        search_filter = Q(code_tiers__icontains=query) | Q(nom_ou_raison_sociale__icontains=query)
        tiers = Tiers.objects.filter(base_filters & tiers_filters & search_filter)
    else:
        tiers = Tiers.objects.filter(base_filters & tiers_filters)
    
    tiers = tiers.order_by('code_tiers')[:50]
    
    return JsonResponse({
        'results': [{
            'code': t.code_tiers,
            'libelle': t.nom_ou_raison_sociale,
            'type': t.type_tiers,
            'compte_associe': t.compte_comptable_associe.numero_compte if t.compte_comptable_associe else None
        } for t in tiers]
    })

@login_required
def journal_info(request, journal_pk):
    """API pour obtenir les informations d'un journal"""
    journal = get_object_or_404(JournalComptable, pk=journal_pk)
    
    return JsonResponse({
        'type': journal.type_journal,
        'compte_contrepartie': journal.compte_contrepartie_par_defaut.numero_compte if journal.compte_contrepartie_par_defaut else None,
        'libelle': journal.libelle,
        'derniere_piece': None  # TODO: Implémenter la récupération du dernier numéro
    })

@login_required
@require_POST
def save_piece(request):
    """API pour sauvegarder une pièce comptable"""
    try:
        data = json.loads(request.body)
        journal = get_object_or_404(JournalComptable, pk=data['journal_pk'])
        
        with transaction.atomic():
            # Créer l'en-tête
            piece = EcritureComptable.objects.create(
                dossier_pme=journal.dossier_pme,
                journal=journal,
                date_ecriture=data['date'],
                numero_piece=data['piece'],
                libelle_piece=data.get('libelle', data['piece'])
            )
            
            # Créer les lignes
            for idx, ligne_data in enumerate(data['lignes']):
                compte = get_object_or_404(
                    CompteComptablePME,
                    dossier_pme=journal.dossier_pme,
                    numero_compte=ligne_data['compte']
                )
                
                tiers = None
                if ligne_data.get('tiers'):
                    tiers = get_object_or_404(
                        Tiers,
                        dossier_pme=journal.dossier_pme,
                        code_tiers=ligne_data['tiers']
                    )
                
                LigneEcriture.objects.create(
                    ecriture=piece,
                    ordre=idx,
                    jour=ligne_data.get('jour'),
                    compte_general=compte,
                    tiers_ligne=tiers,
                    libelle_ligne=ligne_data['libelle'],
                    debit=Decimal(ligne_data.get('debit', '0')),
                    credit=Decimal(ligne_data.get('credit', '0'))
                )
            
            return JsonResponse({'success': True, 'piece_id': piece.id})
    
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def tiers_lookup_view(request, dossier_pk):
    """
    API endpoint to search for business partners (tiers) in a dossier.
    """
    dossier = get_object_or_404(DossierPME, pk=dossier_pk)
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'results': []})
    
    tiers = Tiers.objects.filter(
        Q(code_tiers__icontains=query) | 
        Q(nom_tiers__icontains=query),
        dossier_pme=dossier
    )[:10]
    
    results = [{
        'id': t.code_tiers,
        'text': f"{t.code_tiers} - {t.nom_tiers}",
        'code': t.code_tiers,
        'nom': t.nom_tiers
    } for t in tiers]
    
    return JsonResponse({'results': results})

@login_required
def journal_info_view(request, journal_pk):
    """
    API endpoint to get journal information.
    """
    journal = get_object_or_404(JournalComptable, pk=journal_pk)
    
    info = {
        'code': journal.code_journal,
        'type': journal.type_journal,
        'contrepartie_auto': journal.compte_contrepartie.numero_compte if journal.compte_contrepartie else None,
    }
    
    return JsonResponse(info)

@login_required
@require_POST
@transaction.atomic
def save_piece_view(request):
    """
    API endpoint to save a complete accounting entry (piece).
    """
    try:
        data = json.loads(request.body)
        
        # Get the journal
        journal = get_object_or_404(JournalComptable, pk=data['journal_id'])
        
        # Create the accounting entry
        ecriture = EcritureComptable.objects.create(
            journal=journal,
            date_ecriture=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            numero_piece=data['numero_piece'],
            reference=data.get('reference', ''),
            libelle=data.get('libelle', ''),
            dossier_pme=journal.dossier_pme
        )
        
        # Create lines
        for ligne in data['lignes']:
            compte = get_object_or_404(CompteComptablePME, 
                                     numero_compte=ligne['compte'],
                                     dossier_pme=journal.dossier_pme)
            
            LigneEcriture.objects.create(
                ecriture=ecriture,
                compte=compte,
                debit=Decimal(str(ligne.get('debit', '0'))),
                credit=Decimal(str(ligne.get('credit', '0'))),
                date_echeance=datetime.strptime(ligne['echeance'], '%Y-%m-%d').date() if ligne.get('echeance') else None,
                code_tiers=ligne.get('tiers'),
                libelle=ligne.get('libelle', '')
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Pièce enregistrée avec succès',
            'id': ecriture.pk
        })
        
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de l\'enregistrement: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Erreur serveur lors de l\'enregistrement'
        }, status=500)

@login_required
def get_adjacent_piece(request, dossier_pk, journal_pk, piece_number, direction):
    """Get previous or next piece relative to the current one."""
    journal = get_object_or_404(JournalComptable, pk=journal_pk, dossier_pme__pk=dossier_pk)
    
    try:
        current_piece = EcritureComptable.objects.get(
            journal=journal,
            numero_piece=piece_number
        )
        
        # Chercher la pièce adjacente
        if direction == 'prev':
            piece = EcritureComptable.objects.filter(
                journal=journal,
                date_ecriture__lte=current_piece.date_ecriture,
                numero_piece__lt=piece_number
            ).order_by('-date_ecriture', '-numero_piece').first()
        else:
            piece = EcritureComptable.objects.filter(
                journal=journal,
                date_ecriture__gte=current_piece.date_ecriture,
                numero_piece__gt=piece_number
            ).order_by('date_ecriture', 'numero_piece').first()
        
        if piece:
            return JsonResponse({
                'success': True,
                'piece': piece.to_dict()
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Pas de pièce {direction == "prev" and "précédente" or "suivante"}'
            })
            
    except EcritureComptable.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Pièce non trouvée'
        })

@login_required
def search_pieces(request, dossier_pk, journal_pk):
    """Search for pieces based on criteria."""
    journal = get_object_or_404(JournalComptable, pk=journal_pk, dossier_pme__pk=dossier_pk)
    
    # Extraire les critères de recherche
    piece_number = request.GET.get('pieceNumber')
    date_start = request.GET.get('dateStart')
    date_end = request.GET.get('dateEnd')
    amount = request.GET.get('amount')
    
    # Construire la requête
    pieces = EcritureComptable.objects.filter(journal=journal)
    
    if piece_number:
        pieces = pieces.filter(numero_piece__icontains=piece_number)
    
    if date_start:
        pieces = pieces.filter(date_ecriture__gte=date_start)
    
    if date_end:
        pieces = pieces.filter(date_ecriture__lte=date_end)
    
    if amount:
        amount = Decimal(amount.replace(',', '.'))
        pieces = pieces.filter(
            Q(lignes__debit=amount) | Q(lignes__credit=amount)
        ).distinct()
    
    # Convertir les résultats
    results = [{
        'numero': p.numero_piece,
        'date': p.date_ecriture.isoformat(),
        'reference': p.reference or '',
        'montant': sum(l.debit for l in p.lignes.all())
    } for p in pieces[:50]]  # Limiter à 50 résultats
    
    return JsonResponse({
        'success': True,
        'results': results
    })

@login_required
def suggest_piece_number(request, dossier_pk, journal_pk):
    """Get suggested piece number for new piece."""
    journal = get_object_or_404(JournalComptable, pk=journal_pk, dossier_pme__pk=dossier_pk)
    
    # Trouver le dernier numéro utilisé
    last_piece = EcritureComptable.objects.filter(
        journal=journal,
        date_ecriture__year=datetime.now().year
    ).order_by('-numero_piece').first()
    
    if last_piece:
        # Extraire le numéro séquentiel et l'incrémenter
        try:
            prefix = ''.join(c for c in last_piece.numero_piece if not c.isdigit())
            number = int(''.join(c for c in last_piece.numero_piece if c.isdigit()))
            next_number = f"{prefix}{number + 1:04d}"
        except ValueError:
            next_number = f"{journal.code_journal}{datetime.now().year % 100}0001"
    else:
        # Premier numéro de l'année
        next_number = f"{journal.code_journal}{datetime.now().year % 100}0001"
    
    return JsonResponse({
        'success': True,
        'numero': next_number
    })

@login_required
@require_POST
def validate_piece(request):
    """Validate piece data before saving."""
    try:
        data = json.loads(request.body)
        
        # Vérifications de base
        if not data.get('numero'):
            return JsonResponse({
                'success': False,
                'message': 'Le numéro de pièce est obligatoire'
            })
        
        if not data.get('date'):
            return JsonResponse({
                'success': False,
                'message': 'La date est obligatoire'
            })
        
        if not data.get('lines'):
            return JsonResponse({
                'success': False,
                'message': 'Au moins une ligne est requise'
            })
        
        # Vérifier l'équilibre
        total_debit = sum(Decimal(str(line.get('debit', 0))) for line in data['lines'])
        total_credit = sum(Decimal(str(line.get('credit', 0))) for line in data['lines'])
        
        if total_debit != total_credit:
            return JsonResponse({
                'success': False,
                'message': 'La pièce n\'est pas équilibrée'
            })
        
        return JsonResponse({'success': True})
        
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur de validation : {str(e)}'
        })