# comptabilite/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
# from django.contrib import messages # Décommentez si vous utilisez messages.warning etc.

from .models import (
    CompteComptableDefaut, CompteComptablePME, 
    JournalComptable, 
    EcritureComptable, LigneEcriture, 
    Tiers,
    TauxDeTaxe
)

@admin.register(CompteComptableDefaut)
class CompteComptableDefautAdmin(admin.ModelAdmin):
    list_display = ('numero_compte', 'intitule_compte', 'type_compte', 'nature_compte', 'compte_parent_syscohada', 'est_lettrable_par_defaut')
    list_filter = ('type_compte', 'nature_compte', 'est_lettrable_par_defaut')
    search_fields = ('numero_compte', 'intitule_compte')
    ordering = ('numero_compte',)
    raw_id_fields = ('compte_parent_syscohada',)

@admin.register(CompteComptablePME)
class CompteComptablePMEAdmin(admin.ModelAdmin):
    list_display = ('numero_compte', 'intitule_compte', 'dossier_pme', 'type_compte', 'nature_compte', 'compte_parent', 'est_lettrable', 'est_actif')
    list_filter = ('dossier_pme__nom_dossier', 'type_compte', 'nature_compte', 'est_lettrable', 'est_actif')
    search_fields = ('numero_compte', 'intitule_compte', 'dossier_pme__nom_dossier')
    list_editable = ('est_lettrable', 'est_actif') # Attention avec list_editable sur des champs relationnels ou booléens complexes
    ordering = ('dossier_pme__nom_dossier', 'numero_compte')
    raw_id_fields = ('dossier_pme', 'compte_parent', 'compte_syscohada_ref')
    fieldsets = (
        (_('Appartenance et Référence'), {'fields': ('dossier_pme', 'compte_syscohada_ref')}),
        (_('Détails du Compte (Plan PME)'), {'fields': ('numero_compte', 'intitule_compte', 'type_compte', 'nature_compte', 'compte_parent')}),
        (_('Paramètres Comptables'), {'fields': ('sens_habituel', 'est_lettrable', 'est_actif')}),
        (_('Informations Complémentaires'), {'fields': ('notes',), 'classes': ('collapse',)})
    )

@admin.register(JournalComptable)
class JournalComptableAdmin(admin.ModelAdmin):
    list_display = ('code_journal', 'libelle', 'type_journal', 'dossier_pme', 'compte_contrepartie_par_defaut', 'est_actif')
    list_filter = ('dossier_pme__nom_dossier', 'type_journal', 'est_actif')
    search_fields = ('code_journal', 'libelle', 'dossier_pme__nom_dossier')
    autocomplete_fields = ['dossier_pme', 'compte_contrepartie_par_defaut']
    list_editable = ('est_actif',)
    ordering = ('dossier_pme__nom_dossier', 'code_journal')

@admin.register(Tiers)
class TiersAdmin(admin.ModelAdmin):
    list_display = (
        'code_tiers', 
        'nom_ou_raison_sociale', 
        'type_tiers', 
        'get_dossier_pme_nom', # Utiliser une méthode pour l'affichage de la ForeignKey
        'ville',                 
        'telephone_principal',   
        'get_compte_associe_numero', # Utiliser une méthode
        'est_actif'
    )
    list_filter = (
        # Pour ForeignKey, il est préférable de filtrer par un champ spécifique du modèle lié
        ('dossier_pme', admin.RelatedOnlyFieldListFilter), # Ou 'dossier_pme__nom_dossier'
        'type_tiers', 
        'est_actif', 
        'ville',                 
        'pays'                   
    )
    search_fields = (
        'code_tiers', 
        'nom_ou_raison_sociale', 
        'prenom', 
        'rccm', 
        'compte_contribuable', 
        'email', 
        'telephone_principal', 
        'dossier_pme__nom_dossier',
        'ville', 
        'pays'   
    )
    list_editable = ('est_actif',)
    autocomplete_fields = ['dossier_pme', 'compte_comptable_associe']
    ordering = ('dossier_pme__nom_dossier', 'nom_ou_raison_sociale')
    
    fieldsets = (
        (_('Identification du Tiers'), {'fields': ('dossier_pme', 'code_tiers', 'type_tiers', 'nom_ou_raison_sociale', 'prenom')}),
        (_('Coordonnées'), {'fields': ('adresse_ligne1', 'adresse_ligne2', 'code_postal', 'ville', 'pays', 'telephone_principal', 'telephone_secondaire', 'email', 'site_web'), 'classes': ('collapse',)}),
        (_('Informations Légales et Fiscales (CI)'), {'fields': ('rccm', 'compte_contribuable'), 'classes': ('collapse',)}),
        (_('Paramètres Comptables et État'), {'fields': ('compte_comptable_associe', 'est_actif')}),
        (_('Autres Informations'), {'fields': ('notes',), 'classes': ('collapse',)}),
    )

    @admin.display(description=_('Dossier PME'), ordering='dossier_pme__nom_dossier')
    def get_dossier_pme_nom(self, obj):
        return obj.dossier_pme.nom_dossier if obj.dossier_pme else '-'

    @admin.display(description=_('Cpte Associé'), ordering='compte_comptable_associe__numero_compte')
    def get_compte_associe_numero(self, obj):
        return obj.compte_comptable_associe.numero_compte if obj.compte_comptable_associe else '-'


@admin.register(TauxDeTaxe)
class TauxDeTaxeAdmin(admin.ModelAdmin):
    list_display = ('code_taxe', 'libelle', 'type_taxe', 'taux', 'get_compte_de_taxe_numero', 'get_dossier_pme_nom', 'est_actif')
    list_filter = (('dossier_pme', admin.RelatedOnlyFieldListFilter), 'type_taxe', 'est_actif')
    search_fields = ('code_taxe', 'libelle', 'compte_de_taxe__numero_compte', 'compte_de_taxe__intitule_compte', 'dossier_pme__nom_dossier')
    autocomplete_fields = ['dossier_pme', 'compte_de_taxe']
    list_editable = ('taux', 'est_actif')
    ordering = ('dossier_pme__nom_dossier', 'type_taxe', 'code_taxe')
    fieldsets = (
        (None, {'fields': ('dossier_pme', 'code_taxe', 'libelle', 'type_taxe')}),
        (_('Valeur et Imputation'), {'fields': ('taux', 'compte_de_taxe')}),
        (_('Statut'), {'fields': ('est_actif',)}),
    )

    @admin.display(description=_('Dossier PME'), ordering='dossier_pme__nom_dossier')
    def get_dossier_pme_nom(self, obj):
        return obj.dossier_pme.nom_dossier if obj.dossier_pme else '-'

    @admin.display(description=_('Cpte de Taxe'), ordering='compte_de_taxe__numero_compte')
    def get_compte_de_taxe_numero(self, obj):
        return obj.compte_de_taxe.numero_compte if obj.compte_de_taxe else '-'

class LigneEcritureInline(admin.TabularInline):
    model = LigneEcriture
    extra = 2 
    autocomplete_fields = ['compte_general', 'tiers_ligne'] 
    fields = ('compte_general', 'tiers_ligne', 'libelle_ligne', 'reference_ligne', 'date_echeance_ligne', 'debit', 'credit', 'lettrage_code')
    # classes = ['collapse'] 

@admin.register(EcritureComptable)
class EcritureComptableAdmin(admin.ModelAdmin):
    list_display = (
        'date_ecriture', 'journal', 'numero_piece', 'libelle_piece', 
        'numero_facture_liee', 'get_tiers_en_tete_nom', 'get_dossier_pme_nom', 
        'total_debit_lignes', 'total_credit_lignes', 'est_equilibree'
    )
    list_filter = (('dossier_pme', admin.RelatedOnlyFieldListFilter), ('journal', admin.RelatedOnlyFieldListFilter), 'date_ecriture', ('tiers_en_tete', admin.RelatedOnlyFieldListFilter))
    search_fields = (
        'libelle_piece', 'numero_piece', 'numero_facture_liee',
        'tiers_en_tete__nom_ou_raison_sociale', 
        'journal__code_journal', 'journal__libelle', 
        'lignes_ecriture__libelle_ligne', 
        'lignes_ecriture__compte_general__numero_compte'
    )
    inlines = [LigneEcritureInline]
    date_hierarchy = 'date_ecriture'
    autocomplete_fields = ['dossier_pme', 'journal', 'tiers_en_tete']
    ordering = ('-date_ecriture', '-id')
    fieldsets = (
        (None, {'fields': ('dossier_pme', 'journal', 'date_ecriture', 'numero_piece', 'libelle_piece')}),
        (_('Informations de Pièce Complémentaires'), { 
            'fields': ('numero_facture_liee', 'reference_piece', 'tiers_en_tete', 'date_echeance_piece', 'montant_total_controle'),
            'classes': ('collapse',), 
        }),
    )
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'lignes_ecriture__compte_general', 'lignes_ecriture__tiers_ligne',   
            'journal', 'tiers_en_tete', 'dossier_pme'
        )

    @admin.display(description=_('Dossier PME'), ordering='dossier_pme__nom_dossier')
    def get_dossier_pme_nom(self, obj):
        return obj.dossier_pme.nom_dossier if obj.dossier_pme else '-'
    
    @admin.display(description=_('Tiers en-tête'), ordering='tiers_en_tete__nom_ou_raison_sociale')
    def get_tiers_en_tete_nom(self, obj):
        return obj.tiers_en_tete.nom_ou_raison_sociale if obj.tiers_en_tete else '-'