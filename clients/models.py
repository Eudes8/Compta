from django.db import models

class Client(models.Model):
    JURIDICAL_FORMS = [
        ('SARL', 'SARL'),
        ('SA', 'SA'),
        ('SNC', 'SNC'),
        # Add other forms as needed
    ]

    ACTIVITY_SECTORS = [
        ('Commerce', 'Commerce'),
        ('BTP', 'BTP'),
        ('Transport', 'Transport'),
        # Add other sectors as needed
    ]

    FISCAL_PERIODICITIES = [
        ('Mensuelle', 'Mensuelle'),
        ('Trimestrielle', 'Trimestrielle'),
    ]

    company_name = models.CharField(max_length=255, verbose_name="Nom de l’entreprise")
    acronym = models.CharField(max_length=50, blank=True, null=True, verbose_name="Sigle")
    rccm_number = models.CharField(max_length=100, unique=True, verbose_name="Numéro RCCM")
    ncc_number = models.CharField(max_length=100, unique=True, verbose_name="Numéro NCC")
    juridical_form = models.CharField(max_length=50, choices=JURIDICAL_FORMS, verbose_name="Forme juridique")
    activity_sector = models.CharField(max_length=100, choices=ACTIVITY_SECTORS, verbose_name="Secteur d’activité")
    address = models.CharField(max_length=255, verbose_name="Adresse")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    management_start_date = models.DateField(verbose_name="Date de début de gestion")
    fiscal_periodicity = models.CharField(max_length=20, choices=FISCAL_PERIODICITIES, verbose_name="Périodicité fiscale")

    def __str__(self):
        return self.company_name
