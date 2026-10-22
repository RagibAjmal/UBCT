"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from grants import views as grant_views # Add this import
from finance import views as finance_views # Add this import

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('dashboard/', grant_views.dashboard, name='dashboard'), 
    path('beneficiary/add/', grant_views.create_beneficiary, name='create_beneficiary'),
    path('request/new/', grant_views.create_request, name='create_request'),
    path('request/<int:pk>/edit/', grant_views.edit_request, name='edit_request'),
    path('request/<int:pk>/approve/', grant_views.approve_request, name='approve_request'),
    path('request/<int:pk>/transfer/', grant_views.process_transfer, name='process_transfer'),
    path('request/<int:pk>/', grant_views.request_detail, name='request_detail'),
    path('request/<int:pk>/add-transfer/', finance_views.add_fund_transfer, name='add_fund_transfer'),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('requests/<int:pk>/documents/upload/',grant_views.upload_request_documents, name='upload_request_documents',),
    path("requests/<int:pk>/documents/upload/", grant_views.upload_request_documents, name="upload_request_documents",),
    path("requests/<int:pk>/submit-for-approval/",grant_views.submit_for_approval, name="submit_for_approval",),
    path("request/<int:pk>/documents/<int:document_pk>/delete/", grant_views.delete_request_document, name="delete_request_document",),
    path("request/<int:pk>/documents/<int:document_pk>/tag/", grant_views.tag_request_document, name="tag_request_document",),
    # Uploaded documents are served through permission-checked download views.
    path("request/<int:pk>/documents/<int:document_pk>/download/", grant_views.download_request_document, name="download_request_document",),
    path("transfers/<int:transfer_pk>/documents/", finance_views.fund_transfer_documents, name="fund_transfer_documents",),
    path("transfers/<int:transfer_pk>/documents/<int:document_pk>/download/", finance_views.download_fund_transfer_document, name="download_fund_transfer_document",),
    path("transfers/<int:transfer_pk>/documents/upload/", finance_views.upload_fund_transfer_documents, name="upload_fund_transfer_documents",),
    path("transfers/<int:transfer_pk>/documents/<int:document_pk>/tag/", finance_views.tag_fund_transfer_document, name="tag_fund_transfer_document",),
    path("transfers/<int:transfer_pk>/documents/<int:document_pk>/delete/", finance_views.delete_fund_transfer_document, name="delete_fund_transfer_document",),
    path("requests/", grant_views.all_requests, name="all_requests"),
]