# comptabilite/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from dossiers_pme.models import DossierPME
from .models import CompteComptableDefaut, CompteComptablePME

@receiver(post_save, sender=DossierPME)
def creer_plan_comptable_pour_nouveau_dossier(sender, instance, created, **kwargs):
    if created:
        if not CompteComptablePME.objects.filter(dossier_pme=instance).exists():
            comptes_defaut_dict = {
                cd.numero_compte: cd for cd in CompteComptableDefaut.objects.all()
            }
            
            comptes_pme_a_creer = []
            comptes_pme_crees_dict = {} # Pour retrouver les PKs des parents PME

            # Première passe : créer les comptes sans les parents
            for compte_defaut in CompteComptableDefaut.objects.order_by('numero_compte'): # Ordonner peut aider pour la hiérarchie
                compte_pme = CompteComptablePME(
                    dossier_pme=instance,
                    compte_syscohada_ref=compte_defaut,
                    numero_compte=compte_defaut.numero_compte,
                    intitule_compte=compte_defaut.intitule_compte,
                    type_compte=compte_defaut.type_compte,
                    nature_compte=compte_defaut.nature_compte,
                    sens_habituel=compte_defaut.sens_habituel,
                    est_lettrable=compte_defaut.est_lettrable_par_defaut,
                    est_actif=True
                )
                comptes_pme_a_creer.append(compte_pme)
            
            CompteComptablePME.objects.bulk_create(comptes_pme_a_creer)
            
            # Remplir le dictionnaire avec les comptes PME créés et leur PK
            for compte_pme_cree in CompteComptablePME.objects.filter(dossier_pme=instance):
                comptes_pme_crees_dict[compte_pme_cree.numero_compte] = compte_pme_cree

            # Deuxième passe : assigner les parents
            comptes_pme_a_updater = []
            for compte_defaut in CompteComptableDefaut.objects.filter(compte_parent_syscohada__isnull=False):
                compte_pme_enfant = comptes_pme_crees_dict.get(compte_defaut.numero_compte)
                if compte_pme_enfant and compte_defaut.compte_parent_syscohada:
                    compte_pme_parent = comptes_pme_crees_dict.get(compte_defaut.compte_parent_syscohada.numero_compte)
                    if compte_pme_parent:
                        compte_pme_enfant.compte_parent = compte_pme_parent
                        comptes_pme_a_updater.append(compte_pme_enfant)
            
            if comptes_pme_a_updater:
                CompteComptablePME.objects.bulk_update(comptes_pme_a_updater, ['compte_parent'])

            print(f"Plan comptable par défaut initialisé pour le dossier {instance.nom_dossier}")