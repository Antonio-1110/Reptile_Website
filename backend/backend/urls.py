"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import path, include

from account.views import SellerProfile, SellerReviews
from auction import ecpay
from authentication.lockout import LockoutAdminAuthenticationForm, LockoutAuthenticationForm
from features.views import FeatureSwitches
from post.sitemap import sitemap

admin.site.login_form = LockoutAdminAuthenticationForm

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    # Every endpoint lives under /api/v1/: URL segments are plural, kebab-case nouns; JSON fields are snake_case.
    path('api/v1/auth/', include('authentication.urls')),
    path('api/v1/account/', include('account.urls')),
    path('api/v1/posts/', include('post.urls')),
    path('api/v1/sellers/<int:pk>/', SellerProfile.as_view(), name='seller-profile'),
    path('api/v1/sellers/<int:pk>/reviews/', SellerReviews.as_view(), name='seller-reviews'),
    path('api/v1/auctions/', include('auction.urls')),
    path('api/v1/features/', FeatureSwitches.as_view(), name='features'),
    # Payment provider callbacks (form posts from ECPay, not part of the JSON API).
    path('payments/ecpay/notify/', ecpay.notify, name='ecpay-notify'),
    path('payments/ecpay/result/', ecpay.result, name='ecpay-result'),
    # The browsable API's session login, with the same lockout as the admin (listed first so it wins).
    path('api-auth/login/', LoginView.as_view(
        template_name='rest_framework/login.html', authentication_form=LockoutAuthenticationForm,
    ), name='api-login'),
    path('api-auth/', include('rest_framework.urls')),
    # Served at www.reptilian.app/sitemap.xml through a Vercel rewrite (see post/sitemap.py).
    path('sitemap.xml', sitemap, name='sitemap'),
]

# Uploaded listing photos in local development; in production they live on S3 (see STORAGES).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
