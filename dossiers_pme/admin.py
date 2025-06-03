# dossiers_pme/admin.py
from django.contrib import admin
from .models import DossierPME

@admin.register(DossierPME)
class DossierPMEAdmin(admin.ModelAdmin):
    list_display = (
        'nom_dossier',
        'numero_rccm',
        'numero_compte_contribuable',
        'statut_dossier',
        'gestionnaire_principal',
        'date_derniere_modification'
    )
    list_filter = (
        'statut_dossier',
        'forme_juridique',
        'regime_fiscal_tva',
        'gestionnaire_principal',
        'secteur_activite' # Ajouté
    )
    search_fields = (
        'nom_dossier',
        'numero_rccm',
        'numero_compte_contribuable',
        'email_contact'
    )
    readonly_fields = (
        'date_creation_dossier_optimagest', # Renommé
        'date_derniere_modification'
    )
    fieldsets = (
        (None, {
            'fields': ('nom_dossier', 'numero_rccm', 'numero_compte_contribuable', 'statut_dossier')
        }),
        ('Coordonnées', {
            'fields': ('adresse_siege', 'telephone_standard', 'email_contact', 'site_web'),
            'classes': ('collapse',),
        }),
        ('Informations Légales et Fiscales', {
            'fields': (
                'forme_juridique',
                'secteur_activite',
                'date_creation_entreprise', # Ajouté
                'date_debut_exercice_comptable', # Renommé/clarifié
                'regime_fiscal_tva',
                'centre_impots_rattachement' # Ajouté
            ),
            'classes': ('collapse',),
        }),
        ('Gestion Interne', {
            'fields': ('gestionnaire_principal', 'notes_internes'),
        }),
        ('Timestamps', {
            'fields': ('date_creation_dossier_optimagest', 'date_derniere_modification'), # Renommé
            'classes': ('collapse',),
        }),
    )