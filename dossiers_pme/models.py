# dossiers_pme/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class DossierPME(models.Model):
    # --- Choix pour les champs CharField spécifiques à la Côte d'Ivoire / OHADA ---
    STATUT_CHOICES = [
        ('ACTIF', _('Actif')),
        ('INACTIF', _('Inactif')),
        ('ARCHIVE', _('Archivé')),
        ('PROSPECT', _('Prospect')),
        ('EN_CREATION', _('En création')),
    ]

    FORME_JURIDIQUE_CHOICES_CI = [
        ('EI', _('Entreprise Individuelle')),
        ('SARL', _('SARL (Société à Responsabilité Limitée)')),
        ('SUARL', _('SUARL (Société Unipersonnelle à Responsabilité Limitée)')),
        ('SA', _('SA (Société Anonyme)')),
        ('SAS', _('SAS (Société par Actions Simplifiée)')),
        ('SNC', _('SNC (Société en Nom Collectif)')),
        ('SCS', _('SCS (Société en Commandite Simple)')),
        ('GIE', _('GIE (Groupement d\'Intérêt Économique)')),
        ('COOPERATIVE', _('Société Coopérative')),
        ('AUTRE', _('Autre')),
    ]

    REGIME_FISCAL_TVA_CHOICES_CI = [
        ('RNI', _('Réel Normal d\'Imposition (TVA)')),
        ('RSI', _('Réel Simplifié d\'Imposition (TVA)')),
        ('IS', _('Impôt Synthétique (non assujetti TVA ou régime spécifique)')),
        ('FRANCHISE', _('Franchise en base de TVA')),
        ('EXONERE', _('Exonéré de TVA')),
        ('NON_APPLICABLE', _('Non Applicable')),
        ('AUTRE', _('Autre')),
    ]

    # --- Informations générales ---
    nom_dossier = models.CharField(
        _("Nom du dossier / Raison sociale"),
        max_length=255,
        help_text=_("Nom officiel de la PME ou nom du dossier client.")
    )
    # En Côte d'Ivoire, on a le RCCM et le NCC (Numéro de Compte Contribuable)
    numero_rccm = models.CharField(
        _("Numéro RCCM"),
        max_length=50,
        unique=True, # Un RCCM doit être unique
        blank=True,
        null=True,
        help_text=_("Numéro d'immatriculation au Registre du Commerce et du Crédit Mobilier.")
    )
    numero_compte_contribuable = models.CharField(
        _("Numéro de Compte Contribuable (NCC)"),
        max_length=50,
        unique=True, # Un NCC doit être unique
        blank=True,
        null=True,
        help_text=_("Numéro de Compte Contribuable auprès de la DGI.")
    )
    adresse_siege = models.TextField(
        _("Adresse du siège social"),
        blank=True,
        null=True
    )
    telephone_standard = models.CharField(
        _("Téléphone standard"),
        max_length=30, # Peut inclure indicatifs
        blank=True,
        null=True
    )
    email_contact = models.EmailField(
        _("Email de contact principal"),
        blank=True,
        null=True
    )
    site_web = models.URLField(
        _("Site web"),
        blank=True,
        null=True
    )

    # --- Informations légales et fiscales ---
    forme_juridique = models.CharField(
        _("Forme juridique"),
        max_length=20,
        choices=FORME_JURIDIQUE_CHOICES_CI,
        blank=True,
        null=True
    )
    secteur_activite = models.CharField( # On pourrait utiliser un code NAE/APE ivoirien à terme
        _("Secteur d'activité principal"),
        max_length=255,
        blank=True,
        null=True
    )
    date_creation_entreprise = models.DateField(
        _("Date de création de l'entreprise"),
        blank=True,
        null=True,
    )
    date_debut_exercice_comptable = models.DateField(
        _("Date de début de l'exercice comptable en cours"),
        blank=True,
        null=True,
        help_text=_("Typiquement le 1er Janvier.")
    )
    regime_fiscal_tva = models.CharField(
        _("Régime fiscal / TVA"),
        max_length=20,
        choices=REGIME_FISCAL_TVA_CHOICES_CI,
        blank=True,
        null=True
    )
    centre_impots_rattachement = models.CharField(
        _("Centre des Impôts de rattachement"),
        max_length=100,
        blank=True,
        null=True,
    )

    # --- Gestion interne et statut ---
    statut_dossier = models.CharField(
        _("Statut du dossier"),
        max_length=15, # Augmenté pour 'EN_CREATION'
        choices=STATUT_CHOICES,
        default='ACTIF'
    )
    gestionnaire_principal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Gestionnaire principal du dossier"),
        related_name='dossiers_geres'
    )
    notes_internes = models.TextField(
        _("Notes internes"),
        blank=True,
        null=True,
        help_text=_("Informations réservées à l'usage interne du cabinet.")
    )

    # --- Timestamps ---
    date_creation_dossier_optimagest = models.DateTimeField( # Renommé pour clarté
        _("Date de création du dossier dans OptimaGest"),
        auto_now_add=True
    )
    date_derniere_modification = models.DateTimeField(
        _("Date de dernière modification"),
        auto_now=True
    )

    def __str__(self):
        return f"{self.nom_dossier} ({self.numero_rccm or self.numero_compte_contribuable or _('Non identifié')})"

    class Meta:
        verbose_name = _("Dossier PME (Côte d'Ivoire)")
        verbose_name_plural = _("Dossiers PME (Côte d'Ivoire)")
        ordering = ['nom_dossier']
        constraints = [
            models.UniqueConstraint(fields=['numero_rccm'], name='unique_rccm_if_not_null', condition=models.Q(numero_rccm__isnull=False)),
            models.UniqueConstraint(fields=['numero_compte_contribuable'], name='unique_ncc_if_not_null', condition=models.Q(numero_compte_contribuable__isnull=False)),
        ]