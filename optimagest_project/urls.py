# optimagest_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings # Nécessaire pour settings.DEBUG et les URLs de media/static
from django.conf.urls.static import static # Nécessaire pour servir media/static en dev

urlpatterns = [
    # Interface d'administration Django
    path('admin/', admin.site.urls),

    # Inclure les URLs de votre application 'core'
    # 'core.urls' pointe vers le fichier urls.py dans votre application 'core'
    # 'namespace="core"' permet d'utiliser {% url 'core:nom_de_l_url' %} dans les templates
    path('', include('core.urls', namespace='core')), 

    # Inclure les URLs de votre application 'dossiers_pme'
    # Le préfixe 'dossiers/' signifie que toutes les URLs de 'dossiers_pme.urls'
    # commenceront par /dossiers/
    path('dossiers/', include('dossiers_pme.urls', namespace='dossiers_pme')),

    # Inclure les URLs de votre application 'comptabilite'
    # Le préfixe 'comptabilite/' signifie que toutes les URLs de 'comptabilite.urls'
    # commenceront par /comptabilite/
    path('comptabilite/', include('comptabilite.urls', namespace='comptabilite')),

    # Ajoutez ici d'autres applications si vous en avez
    # Exemple:
    # path('gestion-commerciale/', include('gestion_commerciale.urls', namespace='gescom')),
]

# Configuration pour servir les fichiers statiques et médias en mode DÉVELOPPEMENT uniquement.
# En production, votre serveur web (Nginx, Apache) devrait s'en charger.
if settings.DEBUG:
    # Django gère automatiquement les fichiers statiques via la configuration STATICFILES_DIRS
    # et l'application django.contrib.staticfiles lorsqu'elle est dans INSTALLED_APPS.
    # La ligne ci-dessous est donc généralement pour les fichiers MEDIA.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Si vous avez des configurations spécifiques pour les fichiers statiques que
    # django.contrib.staticfiles ne couvre pas (rare en dev simple), vous pourriez ajouter:
    # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Mais en général, avec `django.contrib.staticfiles` dans `INSTALLED_APPS` et `DEBUG=True`,
    # Django sert les fichiers statiques trouvés via les `STATICFILES_FINDERS` (y compris ceux dans
    # les dossiers 'static' de chaque application et ceux définis dans `STATICFILES_DIRS`).