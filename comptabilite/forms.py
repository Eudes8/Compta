# comptabilite/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory, BaseInlineFormSet
from datetime import date
from decimal import Decimal

from .models import (
    CompteComptablePME, CompteComptableDefaut, 
    JournalComptable, Tiers, TauxDeTaxe, 
    EcritureComptable, LigneEcriture 
)

# --- Formulaire pour CompteComptablePME ---
class CompteComptablePMEForm(forms.ModelForm):
    class Meta:
        model = CompteComptablePME
        fields = [
            'numero_compte', 'intitule_compte', 
            'type_compte', 'nature_compte', 'compte_parent',
            'sens_habituel', 'est_lettrable', 'est_actif', 'notes',
            'compte_syscohada_ref',
        ]
        widgets = {
            'numero_compte': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'intitule_compte': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'type_compte': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'nature_compte': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'compte_parent': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'sens_habituel': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'est_lettrable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'compte_syscohada_ref': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }
        labels = { 
            'numero_compte': _("Numéro de Compte"), 'intitule_compte': _("Intitulé du Compte"),
            'type_compte': _("Type"), 'nature_compte': _("Nature"),
            'compte_parent': _("Compte Parent"), 'sens_habituel': _("Sens Habituel"),
            'est_lettrable': _("Lettrable ?"), 'est_actif': _("Actif ?"),
            'notes': _("Notes"), 'compte_syscohada_ref': _("Réf. SYSCOHADA"),
        }
        help_texts = {
            'numero_compte': _("Numéro unique pour ce compte dans le plan de la PME."),
            'compte_parent': _("Compte de regroupement (laisser vide si c'est un compte racine de classe)."),
            'compte_syscohada_ref': _("Optionnel: Lier à un compte du plan SYSCOHADA standard pour référence."),
        }

    def __init__(self, *args, **kwargs):
        self.dossier_pme = kwargs.pop('dossier_pme', None) 
        super().__init__(*args, **kwargs)
        current_dossier = self.dossier_pme
        if self.instance and self.instance.pk and hasattr(self.instance, 'dossier_pme'):
            current_dossier = self.instance.dossier_pme
        if current_dossier:
            parent_queryset = CompteComptablePME.objects.filter(
                dossier_pme=current_dossier,
                nature_compte__in=['COLLECTIF', 'CENTRALISATEUR']
            ).order_by('numero_compte')
            if self.instance and self.instance.pk: 
                parent_queryset = parent_queryset.exclude(pk=self.instance.pk)
            self.fields['compte_parent'].queryset = parent_queryset
            self.fields['compte_parent'].empty_label = _("--- Aucun (Compte Racine/Classe) ---")
        else:
            self.fields['compte_parent'].queryset = CompteComptablePME.objects.none()
        self.fields['compte_syscohada_ref'].queryset = CompteComptableDefaut.objects.all().order_by('numero_compte')
        self.fields['compte_syscohada_ref'].required = False
        self.fields['compte_syscohada_ref'].empty_label = _("--- Aucune référence SYSCOHADA ---")
        
    def clean_numero_compte(self):
        num = self.cleaned_data.get('numero_compte')
        if num:
            return num.strip()
        return num

    def clean(self):
        cleaned_data = super().clean()
        compte_parent = cleaned_data.get('compte_parent')
        numero_compte = cleaned_data.get('numero_compte')
        dossier_pour_validation = self.dossier_pme
        if self.instance and self.instance.pk: 
            dossier_pour_validation = self.instance.dossier_pme
        if compte_parent and compte_parent.nature_compte == 'DETAIL':
            self.add_error('compte_parent', _("Un compte de détail ne peut pas être un compte parent."))
        if compte_parent and numero_compte and not numero_compte.startswith(compte_parent.numero_compte):
            self.add_error('numero_compte', _("Le numéro de compte doit commencer par le numéro du compte parent."))
        if numero_compte and dossier_pour_validation:
            query = CompteComptablePME.objects.filter(
                dossier_pme=dossier_pour_validation, 
                numero_compte=numero_compte
            )
            if self.instance and self.instance.pk: 
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                self.add_error('numero_compte', _("Ce numéro de compte existe déjà pour ce dossier PME."))
        return cleaned_data

# --- Formulaire pour JournalComptable ---
class JournalComptableForm(forms.ModelForm):
    class Meta:
        model = JournalComptable
        fields = ['code_journal', 'libelle', 'type_journal', 'compte_contrepartie_par_defaut', 'est_actif']
        widgets = {
            'code_journal': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'libelle': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'type_journal': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'compte_contrepartie_par_defaut': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'code_journal': _("Code du Journal"), 
            'libelle': _("Libellé du Journal"),
            'type_journal': _("Type de Journal"), 
            'compte_contrepartie_par_defaut': _("Cpte Contrepartie Défaut"),
            'est_actif': _("Actif ?"),
        }

    def __init__(self, *args, **kwargs):
        dossier_pme_instance = kwargs.pop('dossier_pme', None)
        super().__init__(*args, **kwargs)
        current_dossier = dossier_pme_instance
        if self.instance and self.instance.pk and hasattr(self.instance, 'dossier_pme'): 
            current_dossier = self.instance.dossier_pme
        if current_dossier:
            self.fields['compte_contrepartie_par_defaut'].queryset = CompteComptablePME.objects.filter(
                dossier_pme=current_dossier, 
                est_actif=True, 
                type_compte__in=['TRESORERIE_ACTIF', 'TRESORERIE_PASSIF']
            ).order_by('numero_compte')
            self.fields['compte_contrepartie_par_defaut'].empty_label = _("--- Sélectionner (Optionnel) ---")
        else: 
            self.fields['compte_contrepartie_par_defaut'].queryset = CompteComptablePME.objects.none()
        self.fields['compte_contrepartie_par_defaut'].required = False

    def clean_code_journal(self): 
        code = self.cleaned_data.get('code_journal')
        return code.upper().strip() if code else code

# --- Formulaire pour Tiers ---
class TiersForm(forms.ModelForm):
    class Meta:
        model = Tiers
        exclude = ['dossier_pme', 'date_creation', 'date_mise_a_jour'] 
        widgets = {
            'code_tiers': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'type_tiers': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'nom_ou_raison_sociale': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'adresse_ligne1': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'adresse_ligne2': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'code_postal': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'ville': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'pays': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _("Ex: Côte d'Ivoire")}),
            'telephone_principal': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _("Ex: +225 XX XX XX XX")}),
            'telephone_secondaire': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'site_web': forms.URLInput(attrs={'class': 'form-control form-control-sm'}),
            'rccm': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'compte_contribuable': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'compte_comptable_associe': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'code_tiers': _("Code Tiers"), 'type_tiers': _("Type"),
            'nom_ou_raison_sociale': _("Nom / Raison Sociale"), 'prenom': _("Prénom (si personne physique)"),
            'adresse_ligne1': _("Adresse (Ligne 1)"), 'adresse_ligne2': _("Adresse (Ligne 2)"),
            'telephone_principal': _("Tél. Principal"), 'telephone_secondaire': _("Tél. Secondaire"),
            'compte_contribuable': _("N° Cpt. Contribuable (NCC)"),
            'compte_comptable_associe': _("Cpt. Comptable Général Associé"),
            'est_actif': _("Tiers Actif ?"),
        }
        help_texts = {
            'code_tiers': _("Code unique pour identifier le tiers (ex: CL001, F-TOTAL)."),
            'prenom': _("Laissez vide si c'est une entreprise."),
            'compte_comptable_associe': _("Compte du plan comptable PME (ex: 401xxx, 411xxx) à utiliser par défaut pour ce tiers."),
        }

    def __init__(self, *args, **kwargs):
        self.dossier_pme = kwargs.pop('dossier_pme', None)
        super().__init__(*args, **kwargs)
        current_dossier_for_fk = self.dossier_pme
        if self.instance and self.instance.pk and hasattr(self.instance, 'dossier_pme'):
             current_dossier_for_fk = self.instance.dossier_pme
        
        if current_dossier_for_fk:
            self.fields['compte_comptable_associe'].queryset = CompteComptablePME.objects.filter(
                dossier_pme=current_dossier_for_fk, 
                est_actif=True, 
                nature_compte='DETAIL'
            ).order_by('numero_compte')
        else:
            self.fields['compte_comptable_associe'].queryset = CompteComptablePME.objects.none()
        self.fields['compte_comptable_associe'].required = False
        self.fields['compte_comptable_associe'].empty_label = _("--- Aucun compte associé ---")

    def clean_code_tiers(self):
        code = self.cleaned_data.get('code_tiers')
        return code.upper().strip() if code else code
    
    def clean(self): # Validation supplémentaire
        cleaned_data = super().clean()
        type_tiers = cleaned_data.get('type_tiers')
        prenom = cleaned_data.get('prenom')
        if type_tiers == 'SA' and not prenom: # Si Salarié, prénom est requis
            self.add_error('prenom', _("Le prénom est requis pour un tiers de type 'Salarié'."))
        return cleaned_data


# --- Formulaire pour TauxDeTaxe ---
class TauxDeTaxeForm(forms.ModelForm):
    class Meta:
        model = TauxDeTaxe
        exclude = ['dossier_pme', 'date_creation', 'date_mise_a_jour']
        widgets = {
            'code_taxe': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'libelle': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'type_taxe': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'taux': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.001'}),
            'compte_de_taxe': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'code_taxe': _("Code Taxe"), 'libelle': _("Libellé Taxe"),
            'type_taxe': _("Type de Taxe"), 'taux': _("Taux (%)"),
            'compte_de_taxe': _("Compte Comptable d'Imputation"),
            'est_actif': _("Taxe Active ?"),
        }
        help_texts = {
            'code_taxe': _("Ex: TVA18COL (TVA Collectée 18%), AIRSI."),
            'taux': _("Indiquer le pourcentage. Ex: 18.00 pour 18%."),
            'compte_de_taxe': _("Compte de la classe 4 (ex: 4431, 4452) où la taxe sera enregistrée."),
        }

    def __init__(self, *args, **kwargs):
        self.dossier_pme = kwargs.pop('dossier_pme', None)
        super().__init__(*args, **kwargs)
        current_dossier_for_fk = self.dossier_pme
        if self.instance and self.instance.pk and hasattr(self.instance, 'dossier_pme'):
            current_dossier_for_fk = self.instance.dossier_pme

        if current_dossier_for_fk:
            self.fields['compte_de_taxe'].queryset = CompteComptablePME.objects.filter(
                dossier_pme=current_dossier_for_fk, 
                est_actif=True, 
                nature_compte='DETAIL', 
                numero_compte__startswith='4'
            ).order_by('numero_compte')
        else:
            self.fields['compte_de_taxe'].queryset = CompteComptablePME.objects.none()
        self.fields['compte_de_taxe'].empty_label = _("--- Sélectionner compte d'imputation ---")

    def clean_code_taxe(self):
        code = self.cleaned_data.get('code_taxe')
        return code.upper().strip() if code else code

    def clean_taux(self):
        taux = self.cleaned_data.get('taux')
        if taux is not None and taux < Decimal(0): # Comparer avec Decimal
            raise forms.ValidationError(_("Le taux de taxe ne peut pas être négatif."))
        return taux

# --- Formulaires pour la Saisie des Écritures ---
class SaisieJournalSelectionForm(forms.Form):
    journal = forms.ModelChoiceField(
        queryset=JournalComptable.objects.none(), 
        label=_("Journal"),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    annee = forms.IntegerField(
        label=_("Année"), 
        initial=date.today().year,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm text-center', 'style': 'width: 100px;'})
    )
    MOIS_CHOICES = [ (i, date(2000, i, 1).strftime('%B').capitalize()) for i in range(1, 13) ]
    mois = forms.ChoiceField(
        label=_("Mois"), 
        choices=MOIS_CHOICES, 
        initial=date.today().month,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    def __init__(self, *args, **kwargs):
        dossier_pme = kwargs.pop('dossier_pme', None)
        super().__init__(*args, **kwargs)
        if dossier_pme:
            self.fields['journal'].queryset = JournalComptable.objects.filter(
                dossier_pme=dossier_pme, est_actif=True
            ).order_by('code_journal')
        current_year = date.today().year
        self.fields['annee'].widget.attrs.update({
            'min': current_year - 10, 
            'max': current_year + 2   
        })

    def clean_annee(self):
        annee = self.cleaned_data.get('annee')
        if annee is not None and (annee < 1900 or annee > date.today().year + 10): 
            raise forms.ValidationError(_("L'année semble invalide."))
        return annee
    
    def clean_mois(self):
        mois_str = self.cleaned_data.get('mois')
        if mois_str:
            try:
                mois_int = int(mois_str)
                if not (1 <= mois_int <= 12):
                    raise forms.ValidationError(_("Mois invalide (doit être entre 1 et 12)."))
                return mois_int
            except ValueError:
                raise forms.ValidationError(_("Mois doit être un nombre entier."))
        return None # Ou lever une erreur si le mois est obligatoire et non fourni

class PieceComptableEnTeteForm(forms.ModelForm):
    jour = forms.IntegerField(
        label=_("Jour"), 
        min_value=1, max_value=31, 
        initial=date.today().day,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm text-center', 'style': 'width: 70px;'})
    )
    class Meta:
        model = EcritureComptable
        fields = ['jour', 'numero_piece', 'numero_facture_liee', 'reference_piece', 'tiers_en_tete', 'libelle_piece', 'date_echeance_piece', 'montant_total_controle']
        widgets = {
            'numero_piece': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _("Ex: 000049")}),
            'numero_facture_liee': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'reference_piece': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'tiers_en_tete': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'libelle_piece': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'date_echeance_piece': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'montant_total_controle': forms.NumberInput(attrs={'class': 'form-control form-control-sm text-end', 'step': '0.01'}),
        }
        labels = { 
            'numero_piece': _("N° pièce"), 'numero_facture_liee': _("N° facture"),
            'reference_piece': _("Référence"), 'tiers_en_tete': _("N° compte tiers"),
            'libelle_piece': _("Libellé écriture"), 'date_echeance_piece': _("Date échéance"),
            'montant_total_controle': _("Montant contrôle"), 
        }
    def __init__(self, *args, **kwargs):
        self.dossier_pme = kwargs.pop('dossier_pme', None)
        self.journal = kwargs.pop('journal', None) 
        super().__init__(*args, **kwargs)
        if self.dossier_pme:
            self.fields['tiers_en_tete'].queryset = Tiers.objects.filter(dossier_pme=self.dossier_pme, est_actif=True).order_by('nom_ou_raison_sociale')
            self.fields['tiers_en_tete'].empty_label = _("--- Sélectionner Tiers ---")
        else:
            self.fields['tiers_en_tete'].queryset = Tiers.objects.none()
        self.fields['tiers_en_tete'].required = False
        self.fields['numero_facture_liee'].required = False
        self.fields['reference_piece'].required = False
        self.fields['date_echeance_piece'].required = False
        self.fields['montant_total_controle'].required = False
        self.fields['numero_piece'].required = False 
        self.fields['libelle_piece'].required = True
        if not self.instance.pk and self.journal : 
            if self.journal.type_journal == 'AC': self.initial['libelle_piece'] = _("Facture Achat")
            elif self.journal.type_journal == 'VE': self.initial['libelle_piece'] = _("Facture Vente")

class LigneEcritureSaisieForm(forms.ModelForm):
    class Meta:
        model = LigneEcriture
        fields = ['jour', 'numero_piece', 'numero_facture', 'reference', 'compte_general', 
                 'tiers_ligne', 'libelle_ligne', 'date_echeance_ligne', 'debit', 'credit']
        widgets = {
            'jour': forms.NumberInput(attrs={'class': 'form-control form-control-sm text-center', 'style': 'width: 70px;'}),
            'numero_piece': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _("Ex: 000049")}),
            'numero_facture': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'reference': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'compte_general': forms.Select(attrs={'class': 'form-select form-select-sm compte-general-selector'}),
            'tiers_ligne': forms.Select(attrs={'class': 'form-select form-select-sm compte-tiers-selector'}),
            'libelle_ligne': forms.TextInput(attrs={'class': 'form-control form-control-sm libelle_ligne_input'}),
            'date_echeance_ligne': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'debit': forms.NumberInput(attrs={'class': 'form-control form-control-sm text-end debit-field', 'step': '0.01'}),
            'credit': forms.NumberInput(attrs={'class': 'form-control form-control-sm text-end credit-field', 'step': '0.01'}),
        }
        labels = {
            'jour': _("Jour"),
            'numero_piece': _("N° pièce"),
            'numero_facture': _("N° facture"),
            'reference': _("Référence"),
            'compte_general': _("N° compte..."),
            'tiers_ligne': _("N° compte t..."),
            'libelle_ligne': _("Libellé écriture"),
            'date_echeance_ligne': _("Date échéance"),
            'debit': _("Débit"),
            'credit': _("Crédit"),
        }

    def __init__(self, *args, **kwargs):
        self.dossier_pme = kwargs.pop('dossier_pme', None)
        super().__init__(*args, **kwargs)
        
        if self.dossier_pme:
            self.fields['compte_general'].queryset = CompteComptablePME.objects.filter(
                dossier_pme=self.dossier_pme,
                est_actif=True
            ).order_by('numero_compte')
            
            self.fields['tiers_ligne'].queryset = Tiers.objects.filter(
                dossier_pme=self.dossier_pme,
                est_actif=True
            ).order_by('code_tiers')
        else:
            self.fields['compte_general'].queryset = CompteComptablePME.objects.none()
            self.fields['tiers_ligne'].queryset = Tiers.objects.none()
        
        # Configure field labels and defaults
        self.fields['compte_general'].empty_label = _("N° compte...")
        self.fields['tiers_ligne'].empty_label = _("N° compte t...")
        
        # Required fields
        required_fields = ['compte_general', 'libelle_ligne']
        optional_fields = ['tiers_ligne', 'date_echeance_ligne', 'numero_piece', 
                         'numero_facture', 'reference']
        
        for field in required_fields:
            self.fields[field].required = True
        
        for field in optional_fields:
            self.fields[field].required = False
        
        # Initialize default values for new instances
        if not self.instance.pk:
            self.initial['debit'] = Decimal('0.00')
            self.initial['credit'] = Decimal('0.00')
    def clean(self):
        cleaned_data = super().clean()
        debit = cleaned_data.get('debit')
        credit = cleaned_data.get('credit')
        compte_general = cleaned_data.get('compte_general')
        libelle_ligne = cleaned_data.get('libelle_ligne')
        is_line_intended_to_be_filled = cleaned_data.get('jour') or cleaned_data.get('numero_piece') or cleaned_data.get('numero_facture') or cleaned_data.get('reference') or compte_general or libelle_ligne or (debit and debit != Decimal(0)) or (credit and credit != Decimal(0))
        if self.has_changed() and is_line_intended_to_be_filled:
            if not compte_general: self.add_error('compte_general', _("Un compte est requis."))
            if not libelle_ligne: self.add_error('libelle_ligne', _("Un libellé est requis."))
            if (debit is None or debit == Decimal(0)) and (credit is None or credit == Decimal(0)): self.add_error(None, _("Un montant (débit ou crédit) est requis."))
            elif debit is not None and debit > Decimal(0) and credit is not None and credit > Decimal(0): self.add_error(None, _("Débit et crédit ne peuvent être saisis simultanément."))
            if compte_general and compte_general.type_compte in ['TIERS_CLIENT', 'TIERS_FOURNISSEUR', 'TIERS_SALARIE'] and not cleaned_data.get('tiers_ligne'): self.add_error('tiers_ligne', _("Un compte tiers est requis pour '%(compte)s'.") % {'compte': compte_general.numero_compte})
        return cleaned_data

class BaseLigneEcritureSaisieFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors): return
        total_debit = Decimal(0)
        total_credit = Decimal(0)
        lignes_remplies_actives = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or not form.cleaned_data: continue
            if form.cleaned_data.get('DELETE', False): continue
            compte_general = form.cleaned_data.get('compte_general')
            libelle_ligne = form.cleaned_data.get('libelle_ligne')
            debit = form.cleaned_data.get('debit') or Decimal(0)
            credit = form.cleaned_data.get('credit') or Decimal(0)
            is_active_line = compte_general and libelle_ligne and (debit != Decimal(0) or credit != Decimal(0))
            if is_active_line : 
                lignes_remplies_actives +=1
                total_debit += debit
                total_credit += credit
            elif compte_general and libelle_ligne and debit == Decimal(0) and credit == Decimal(0) and form.has_changed(): 
                form.add_error(None, _("Ligne avec compte/libellé mais sans montant."))
        if lignes_remplies_actives == 0:
            any_changed_not_deleted = False
            for form in self.forms:
                if form.has_changed() and not (hasattr(form, 'cleaned_data') and form.cleaned_data.get('DELETE')):
                    any_changed_not_deleted = True
                    break
            if any_changed_not_deleted: 
                raise forms.ValidationError(_("Veuillez saisir au moins une ligne d'écriture valide."), code='aucune_ligne_valide')
        if abs(total_debit - total_credit) >= Decimal('0.01'): 
            raise forms.ValidationError(_("Pièce déséquilibrée. Débit: %(debit).2f, Crédit: %(credit).2f, Solde: %(diff).2f") % {'debit': total_debit, 'credit': total_credit, 'diff': total_debit - total_credit}, code='desequilibre')

LigneEcritureSaisieFormSet = inlineformset_factory(
    EcritureComptable, 
    LigneEcriture, 
    form=LigneEcritureSaisieForm, 
    formset=BaseLigneEcritureSaisieFormSet,
    fields=(
        'jour', 'numero_piece', 'numero_facture', 'reference',
        'compte_general', 'tiers_ligne', 'libelle_ligne',
        'date_echeance_ligne', 'debit', 'credit'
    ),
    extra=1,  # Une seule ligne vide par défaut
    min_num=1,  # Au moins une ligne requise
    validate_min=True,
    can_delete=True,
    max_num=100  # Limite raisonnable de lignes
)
