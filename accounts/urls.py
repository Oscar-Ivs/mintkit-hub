from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html'
    ), name='login'),

    path('logout/', views.logout_view, name='logout'),

    path('register/', views.register, name='register'),

    path('dashboard/', views.dashboard, name='dashboard'),

    path("profile/edit/", views.edit_profile, name="edit_profile"),

    path("email-preview/<str:kind>/", views.email_preview, name="email_preview"),

    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            subject_template_name="registration/password_reset_subject.txt",
            email_template_name="registration/password_reset_email.txt",
            html_email_template_name="registration/password_reset_email.html",
        ),
        name="password_reset",
    ),

]
