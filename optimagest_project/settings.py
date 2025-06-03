# optimagest_project/settings.py

from pathlib import Path
import os # Pour .env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Gestion des variables d'environnement avec python-dotenv ---
# Assurez-vous d'avoir fait : pip install python-dotenv
from dotenv import load_dotenv
env_path = BASE_DIR / '.env' # Chemin explicite vers .env à la racine du projet
load_dotenv(dotenv_path=env_path)

# SECURITY WARNING: keep the secret key used in production secret!
# Lit 'SECRET_KEY' depuis votre .env. Si non trouvé, utilise une clé par défaut (NE PAS UTILISER EN PROD).
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key-replace-if-not-in-env')

# SECURITY WARNING: don't run with debug turned on in production!
# Lit 'DEBUG' depuis votre .env. Si non trouvé ou vide, la valeur par défaut est 'True'.
# Convertit la string 'True' ou 'False' en booléen.
DEBUG_STR = os.getenv('DEBUG', 'True')
DEBUG = DEBUG_STR.lower() in ('true', '1', 't')

# ALLOWED_HOSTS
# Lit 'ALLOWED_HOSTS' depuis votre .env.
# Si DEBUG est True et que ALLOWED_HOSTS n'est pas dans .env, Django autorise ['localhost', '127.0.0.1']
# Si DEBUG est False, ALLOWED_HOSTS DOIT être défini, sinon Django lèvera une erreur.
allowed_hosts_str = os.getenv('ALLOWED_HOSTS')
if allowed_hosts_str:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',')]
elif not DEBUG:
    ALLOWED_HOSTS = [] # Forcera une erreur en production si non défini, ce qui est souhaitable.
else:
    ALLOWED_HOSTS = [] # En mode DEBUG, Django gère les valeurs par défaut


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize', # Pour les filtres comme intcomma

    # Applications tierces
    'crispy_forms',
    "crispy_bootstrap5",
    'django_htmx',

    # Vos applications
    # Si vous avez des AppConfig personnalisés, utilisez le chemin complet, ex: 'core.apps.CoreConfig'
    # Sinon, juste le nom de l'application suffit.
    # D'après votre apps.py de comptabilite, vous utilisez une AppConfig:
    'core', # Mettez 'core.apps.CoreConfig' si vous avez un CoreConfig
    'dossiers_pme', # Mettez 'dossiers_pme.apps.DossiersPmeConfig' si vous avez un DossiersPmeConfig
    'comptabilite.apps.ComptabiliteConfig', # Vous avez une AppConfig pour comptabilite
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware', # Pour django-htmx
]

ROOT_URLCONF = 'optimagest_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Pour les templates globaux (ex: base.html)
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'optimagest_project.wsgi.application'


# Database
# Lit la configuration de la base de données depuis .env
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', 'optimagest_db_default_name'), # Nom par défaut si non trouvé dans .env
        'USER': os.getenv('DB_USER', 'optimagest_user_default'), # Utilisateur par défaut
        'PASSWORD': os.getenv('DB_PASSWORD', 'password_default'), # Mot de passe par défaut
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan' # UTC est une autre option courante
USE_I18N = True
USE_L10N = True # Active la localisation des formats (dates, nombres)
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
# STATIC_ROOT = BASE_DIR / 'staticfiles_collect' # Décommentez pour `collectstatic` en production
STATICFILES_DIRS = [
    BASE_DIR / "static", # Pour vos fichiers statiques globaux (non liés à une app spécifique)
]

# Media files (User uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Configuration pour Django Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# Configuration de l'Authentification
LOGIN_URL = 'admin:login' # Redirige vers la page de connexion de l'admin
# Assurez-vous que la route 'core:home' existe et est correcte.
# Si vous n'avez pas de 'core:home' pour l'instant, utilisez '/'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home' # Ou '/' après déconnexion


# Configuration des messages Django pour Bootstrap 5 (optionnel mais recommandé)
# from django.contrib.messages import constants as messages_constants
# MESSAGE_TAGS = {
#     messages_constants.DEBUG: 'alert-secondary',
#     messages_constants.INFO: 'alert-info',
#     messages_constants.SUCCESS: 'alert-success',
#     messages_constants.WARNING: 'alert-warning',
#     messages_constants.ERROR: 'alert-danger',
# }