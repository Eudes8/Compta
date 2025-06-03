# comptabilite/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q, Value, F, Max, DecimalField # Ajout de DecimalField, Max
from django.db.models.functions import Coalesce
from dossiers_pme.models import DossierPME # Assurez-vous que l'import est correct
from decimal import Decimal # Pour les valeurs Decimal par défaut

class CompteComptableDefaut(models.Model):
    TYPE_COMPTE_CHOICES = [
        ('BILAN_ACTIF', _('Bilan - Actif')), ('BILAN_PASSIF', _('Bilan - Passif')),
        ('CHARGE', _('Compte de Résultat - Charge')), ('PRODUIT', _('Compte de Résultat - Produit')),
        ('TIERS_CLIENT', _('Tiers - Client')), ('TIERS_FOURNISSEUR', _('Tiers - Fournisseur')),
        ('TIERS_SALARIE', _('Tiers - Salarié')), ('TIERS_ETAT', _('Tiers - État')),
        ('TIERS_ASSOCIE', _('Tiers - Associé/Organisme Social')),
        ('TRESORERIE_ACTIF', _('Trésorerie - Actif')), ('TRESORERIE_PASSIF', _('Trésorerie - Passif')),
        ('AUTRE', _('Autre')),
    ]
    NATURE_COMPTE_CHOICES = [
        ('COLLECTIF', _('Collectif')), ('DETAIL', _('Détail/Mouvementable')),
        ('CENTRALISATEUR', _('Centralisateur')),
    ]
    numero_compte = models.CharField(_("Numéro de compte SYSCOHADA"), max_length=50, unique=True)
    intitule_compte = models.CharField(_("Intitulé du compte SYSCOHADA"), max_length=255)
    type_compte = models.CharField(_("Type de compte"), max_length=50, choices=TYPE_COMPTE_CHOICES, blank=True, null=True)
    nature_compte = models.CharField(_("Nature du compte"), max_length=50, choices=NATURE_COMPTE_CHOICES, default='DETAIL')
    compte_parent_syscohada = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sous_comptes_syscohada', verbose_name=_("Compte parent SYSCOHADA"))
    sens_habituel = models.CharField(_("Sens habituel du solde"), max_length=10, choices=[('DEBIT', _('Débit')), ('CREDIT', _('Crédit'))], blank=True, null=True)
    est_lettrable_par_defaut = models.BooleanField(_("Lettrable par défaut ?"), default=False)
    
    class Meta: 
        verbose_name = _("Compte Comptable SYSCOHADA (Défaut)")
        verbose_name_plural = _("Comptes Comptables SYSCOHADA (Défaut)")
        ordering = ['numero_compte']
    
    def __str__(self): 
        return f"{self.numero_compte} - {self.intitule_compte}"

class CompteComptablePME(models.Model):
    TYPE_COMPTE_CHOICES = CompteComptableDefaut.TYPE_COMPTE_CHOICES
    NATURE_COMPTE_CHOICES = CompteComptableDefaut.NATURE_COMPTE_CHOICES
    
    dossier_pme = models.ForeignKey(DossierPME, on_delete=models.CASCADE, related_name='plan_comptable_personnalise', verbose_name=_("Dossier PME"))
    compte_syscohada_ref = models.ForeignKey(CompteComptableDefaut, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Compte SYSCOHADA de référence"))
    numero_compte = models.CharField(_("Numéro de compte"), max_length=50, help_text=_("Numéro du compte spécifique à la PME."))
    intitule_compte = models.CharField(_("Intitulé du compte"), max_length=255)
    type_compte = models.CharField(_("Type de compte"), max_length=50, choices=TYPE_COMPTE_CHOICES, blank=True, null=True)
    nature_compte = models.CharField(_("Nature du compte"), max_length=50, choices=NATURE_COMPTE_CHOICES, default='DETAIL')
    compte_parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sous_comptes_pme', verbose_name=_("Compte parent (Plan PME)"))
    sens_habituel = models.CharField(_("Sens habituel du solde"), max_length=10, choices=[('DEBIT', _('Débit')), ('CREDIT', _('Crédit'))], blank=True, null=True)
    est_lettrable = models.BooleanField(_("Compte lettrable ?"), default=False)
    est_actif = models.BooleanField(_("Compte actif ?"), default=True)
    notes = models.TextField(_("Notes (spécifiques PME)"), blank=True, default="")
    
    class Meta: 
        verbose_name = _("Compte Comptable PME")
        verbose_name_plural = _("Comptes Comptables PME")
        unique_together = ('dossier_pme', 'numero_compte')
        ordering = ['dossier_pme', 'numero_compte']
        
    def __str__(self): 
        return f"{self.numero_compte} - {self.intitule_compte} ({self.dossier_pme.nom_dossier})"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new and self.compte_syscohada_ref:
            if not self.intitule_compte: self.intitule_compte = self.compte_syscohada_ref.intitule_compte
            if not self.type_compte: self.type_compte = self.compte_syscohada_ref.type_compte
            if not self.nature_compte and self.compte_syscohada_ref.nature_compte: self.nature_compte = self.compte_syscohada_ref.nature_compte
            if not self.sens_habituel: self.sens_habituel = self.compte_syscohada_ref.sens_habituel
            # Gérer est_lettrable explicitement pour éviter des surprises
            if not hasattr(self, '_est_lettrable_explicitly_set'): # Suppose un attribut temporaire si défini via form
                self.est_lettrable = self.compte_syscohada_ref.est_lettrable_par_defaut
        super().save(*args, **kwargs)

class JournalComptable(models.Model):
    TYPE_JOURNAL_CHOICES = [('AC', _('Achats')), ('VE', _('Ventes')), ('BQ', _('Banque')), ('CA', _('Caisse')), ('OD', _('Opérations Diverses')), ('AN', _('À Nouveau'))]
    dossier_pme = models.ForeignKey(DossierPME, on_delete=models.CASCADE, related_name='journaux')
    code_journal = models.CharField(_("Code du journal"), max_length=10)
    libelle = models.CharField(_("Libellé du journal"), max_length=100)
    type_journal = models.CharField(_("Type de journal"), max_length=10, choices=TYPE_JOURNAL_CHOICES)
    compte_contrepartie_par_defaut = models.ForeignKey(
        CompteComptablePME, 
        on_delete=models.SET_NULL, null=True, blank=True, 
        verbose_name=_("Compte de contrepartie par défaut (pour trésorerie)"), 
        limit_choices_to=Q(nature_compte='DETAIL') & (Q(type_compte__in=['TRESORERIE_ACTIF', 'TRESORERIE_PASSIF']) | Q(numero_compte__startswith='5'))
    )
    est_actif = models.BooleanField(_("Journal actif ?"), default=True)
    
    class Meta: 
        verbose_name = _("Journal Comptable")
        verbose_name_plural = _("Journaux Comptables")
        unique_together = ('dossier_pme', 'code_journal')
        ordering = ['dossier_pme', 'code_journal']
        
    def __str__(self): 
        return f"{self.code_journal} - {self.libelle} ({self.dossier_pme.nom_dossier})"

class Tiers(models.Model):
    TYPE_TIERS_CHOICES = [('CL', _('Client')), ('FO', _('Fournisseur')), ('SA', _('Salarié')), ('ET', _('État et Admin. Publiques')), ('OS', _('Organismes Sociaux')), ('DI', _('Divers (Opérations internes)')), ('AU', _('Autre Tiers'))]
    dossier_pme = models.ForeignKey(DossierPME, on_delete=models.CASCADE, related_name='tiers', verbose_name=_("Dossier PME"))
    code_tiers = models.CharField(_("Code Tiers"), max_length=20, help_text=_("Code unique pour ce tiers dans ce dossier PME (ex: CL001, F-DURAND)."))
    type_tiers = models.CharField(_("Type de Tiers"), max_length=2, choices=TYPE_TIERS_CHOICES, default='AU')
    nom_ou_raison_sociale = models.CharField(_("Nom / Raison Sociale"), max_length=255)
    prenom = models.CharField(_("Prénom (si particulier)"), max_length=100, blank=True, default="")
    adresse_ligne1 = models.CharField(_("Adresse Ligne 1"), max_length=255, blank=True, default="")
    adresse_ligne2 = models.CharField(_("Adresse Ligne 2"), max_length=255, blank=True, default="") # Ajouté si manquant
    code_postal = models.CharField(_("Code Postal"), max_length=20, blank=True, default="")       # Ajouté si manquant
    ville = models.CharField(_("Ville"), max_length=100, blank=True, default="")                 # Champ vérifié
    pays = models.CharField(_("Pays"), max_length=100, blank=True, default="Côte d'Ivoire")     # Champ vérifié
    telephone_principal = models.CharField(_("Téléphone Principal"), max_length=30, blank=True, default="") # Champ vérifié
    telephone_secondaire = models.CharField(_("Téléphone Secondaire"), max_length=30, blank=True, default="") # Ajouté si manquant
    email = models.EmailField(_("Adresse Email"), blank=True, default="")                           # Ajouté si manquant
    site_web = models.URLField(_("Site Web"), blank=True, default="")                               # Ajouté si manquant
    rccm = models.CharField(_("RCCM"), max_length=50, blank=True, default="")
    compte_contribuable = models.CharField(_("N° Compte Contribuable (NCC)"), max_length=50, blank=True, default="")
    compte_comptable_associe = models.ForeignKey(
        CompteComptablePME, 
        on_delete=models.SET_NULL, null=True, blank=True, 
        verbose_name=_("Compte Comptable Général Associé"), 
        help_text=_("Compte du plan comptable PME (ex: 401xxx, 411xxx) à utiliser par défaut pour ce tiers."), 
        limit_choices_to=Q(nature_compte='DETAIL') & Q(est_actif=True) & (
            Q(type_compte__in=['TIERS_CLIENT', 'TIERS_FOURNISSEUR', 'TIERS_SALARIE', 'TIERS_ETAT', 'TIERS_ASSOCIE']) | 
            Q(numero_compte__startswith='4')
        )
    )
    notes = models.TextField(_("Notes"), blank=True, default="")
    est_actif = models.BooleanField(_("Tiers Actif ?"), default=True)
    date_creation = models.DateTimeField(_("Date de création"), default=timezone.now, editable=False)
    date_mise_a_jour = models.DateTimeField(_("Date de mise à jour"), auto_now=True)
    
    class Meta: 
        verbose_name = _("Tiers")
        verbose_name_plural = _("Tiers")
        unique_together = ('dossier_pme', 'code_tiers')
        ordering = ['dossier_pme', 'nom_ou_raison_sociale']
        
    def __str__(self): 
        return f"{self.code_tiers} - {self.nom_ou_raison_sociale} ({self.dossier_pme.nom_dossier})"

class TauxDeTaxe(models.Model):
    dossier_pme = models.ForeignKey(DossierPME, on_delete=models.CASCADE, related_name='taux_de_taxes', verbose_name=_("Dossier PME"))
    code_taxe = models.CharField(_("Code Taxe"), max_length=20, help_text=_("Code unique pour cette taxe (ex: TVA18COL)."))
    libelle = models.CharField(_("Libellé de la Taxe"), max_length=100)
    TYPE_TAXE_CHOICES = [('COLLECTEE', _('Taxe Collectée')), ('DEDUCTIBLE', _('Taxe Déductible')), ('AUTRE', _('Autre Taxe'))]
    type_taxe = models.CharField(_("Type de Taxe"), max_length=20, choices=TYPE_TAXE_CHOICES, default='AUTRE')
    taux = models.DecimalField(_("Taux (en %)"), max_digits=6, decimal_places=3, help_text=_("Ex: 18.00 pour 18%."))
    compte_de_taxe = models.ForeignKey(
        CompteComptablePME, 
        on_delete=models.PROTECT, verbose_name=_("Compte Comptable de la Taxe"), 
        limit_choices_to=Q(numero_compte__startswith='4') & Q(nature_compte='DETAIL') & Q(est_actif=True)
    )
    est_actif = models.BooleanField(_("Taux Actif ?"), default=True)
    date_creation = models.DateTimeField(_("Date de création"), default=timezone.now, editable=False)
    date_mise_a_jour = models.DateTimeField(_("Date de mise à jour"), auto_now=True)
    
    class Meta: 
        verbose_name = _("Taux de Taxe"); verbose_name_plural = _("Taux de Taxes")
        unique_together = ('dossier_pme', 'code_taxe'); ordering = ['dossier_pme', 'type_taxe', 'code_taxe']
    def __str__(self): return f"{self.code_taxe} - {self.libelle} ({self.taux}%)"
    def get_taux_decimal(self): return self.taux / Decimal(100) if self.taux is not None else Decimal(0)

class EcritureComptable(models.Model):
    dossier_pme = models.ForeignKey(DossierPME, on_delete=models.CASCADE, related_name='ecritures')
    journal = models.ForeignKey(JournalComptable, on_delete=models.PROTECT, related_name='ecritures')
    date_ecriture = models.DateField(_("Date de la Pièce")) 
    numero_piece = models.CharField(_("N° Pièce"), max_length=50, blank=True, help_text=_("Numéro séquentiel ou manuel."))
    libelle_piece = models.CharField(_("Libellé Pièce"), max_length=255, help_text=_("Libellé général de la pièce."))
    numero_facture_liee = models.CharField(_("N° Facture"), max_length=50, blank=True, null=True)
    reference_piece = models.CharField(_("Référence"), max_length=100, blank=True, null=True)
    tiers_en_tete = models.ForeignKey(Tiers, on_delete=models.SET_NULL, null=True, blank=True, related_name='ecritures_en_tete', verbose_name=_("N° Compte Tiers (en-tête)"))
    date_echeance_piece = models.DateField(_("Date Échéance (en-tête)"), null=True, blank=True)
    montant_total_controle = models.DecimalField(_("Montant Total Contrôle"), max_digits=15, decimal_places=2, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Pièce Comptable"); verbose_name_plural = _("Pièces Comptables")
        ordering = ['dossier_pme', '-date_ecriture', 'journal', '-id']
    def __str__(self): return f"Pièce {self.numero_piece or 'N/A'} du {self.date_ecriture.strftime('%d/%m/%Y')}"
    @property
    def total_debit_lignes(self): return self.lignes_ecriture.aggregate(total=Coalesce(Sum('debit'), Value(Decimal(0)), output_field=DecimalField()))['total']
    @property
    def total_credit_lignes(self): return self.lignes_ecriture.aggregate(total=Coalesce(Sum('credit'), Value(Decimal(0)), output_field=DecimalField()))['total']
    @property
    def solde_piece(self): return self.total_debit_lignes - self.total_credit_lignes
    @property
    def est_equilibree(self): return abs(self.solde_piece) < Decimal('0.001')

class LigneEcriture(models.Model):
    ecriture = models.ForeignKey(EcritureComptable, on_delete=models.CASCADE, related_name='lignes_ecriture')
    compte_general = models.ForeignKey(CompteComptablePME, on_delete=models.PROTECT, limit_choices_to={'nature_compte': 'DETAIL', 'est_actif': True}, verbose_name=_("N° Compte Général"))
    tiers_ligne = models.ForeignKey(Tiers, on_delete=models.SET_NULL, null=True, blank=True, related_name='lignes_ecriture_detail', verbose_name=_("N° Compte Tiers (ligne)"), help_text=_("Si compte général collectif."))
    libelle_ligne = models.CharField(_("Libellé Écriture (ligne)"), max_length=255, help_text=_("Libellé spécifique à cette ligne."))
    date_echeance_ligne = models.DateField(_("Date Échéance (ligne)"), null=True, blank=True)
    lettrage_code = models.CharField(_("Lettrage"), max_length=10, blank=True, null=True )
    jour = models.IntegerField(_("Jour"), blank=True, null=True)
    numero_piece = models.CharField(_("N° Pièce"), max_length=50, blank=True, null=True)
    numero_facture = models.CharField(_("N° Facture"), max_length=50, blank=True, null=True)
    reference = models.CharField(_("Référence"), max_length=100, blank=True, null=True)
    debit = models.DecimalField(_("Débit"), max_digits=15, decimal_places=2, default=Decimal(0))
    credit = models.DecimalField(_("Crédit"), max_digits=15, decimal_places=2, default=Decimal(0))
    ordre = models.PositiveIntegerField(_("Ordre"), default=0, editable=False)

    class Meta:
        verbose_name = _("Ligne de Pièce Comptable"); verbose_name_plural = _("Lignes de Pièces Comptables")
        ordering = ['ecriture', 'ordre', 'id']
    def __str__(self): return f"Ligne pour {self.ecriture.numero_piece or 'N/A'}: Cpte {self.compte_general.numero_compte}"
    def clean(self):
        if (self.debit or Decimal(0)) > Decimal(0) and (self.credit or Decimal(0)) > Decimal(0):
            raise ValidationError(_("Débit et crédit non nuls simultanément interdits."))
    def save(self, *args, **kwargs):
        if not self.pk:
            max_ordre_dict = LigneEcriture.objects.filter(ecriture=self.ecriture).aggregate(max_o=Max('ordre'))
            max_ordre = max_ordre_dict['max_o']
            self.ordre = (max_ordre if max_ordre is not None else -1) + 1
        super().save(*args, **kwargs)