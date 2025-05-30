# Generated by Django 5.2.1 on 2025-05-30 17:29

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(max_length=255, verbose_name='Nom de l’entreprise')),
                ('acronym', models.CharField(blank=True, max_length=50, null=True, verbose_name='Sigle')),
                ('rccm_number', models.CharField(max_length=100, unique=True, verbose_name='Numéro RCCM')),
                ('ncc_number', models.CharField(max_length=100, unique=True, verbose_name='Numéro NCC')),
                ('juridical_form', models.CharField(choices=[('SARL', 'SARL'), ('SA', 'SA'), ('SNC', 'SNC')], max_length=50, verbose_name='Forme juridique')),
                ('activity_sector', models.CharField(choices=[('Commerce', 'Commerce'), ('BTP', 'BTP'), ('Transport', 'Transport')], max_length=100, verbose_name='Secteur d’activité')),
                ('address', models.CharField(max_length=255, verbose_name='Adresse')),
                ('phone', models.CharField(blank=True, max_length=20, null=True, verbose_name='Téléphone')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email')),
                ('management_start_date', models.DateField(verbose_name='Date de début de gestion')),
                ('fiscal_periodicity', models.CharField(choices=[('Mensuelle', 'Mensuelle'), ('Trimestrielle', 'Trimestrielle')], max_length=20, verbose_name='Périodicité fiscale')),
            ],
        ),
    ]
