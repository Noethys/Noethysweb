#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Permission, Group
from django.contrib.admin.widgets import FilteredSelectMultiple, RelatedFieldWidgetWrapper
from core.models import Utilisateur, Structure


# --------------------------- Groupes d'utilisateurs ----------------------------

class GroupAdminForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.exclude(name__startswith='Can').order_by("name"), label="Permissions",
        widget=FilteredSelectMultiple('permissions', False))

    class Meta:
        model = Group
        exclude = ()


class MyGroupAdmin(admin.ModelAdmin):
    form = GroupAdminForm


admin.site.unregister(Group)
admin.site.register(Group, MyGroupAdmin)


# --------------------------- Modification du formulaire (permissions)  ----------------------------

class FilteredSelectMultiplePermissions(FilteredSelectMultiple):
    """ Permet de contourner le bug du label placé à droite du widget au lieu de la gauche """
    class Media:
        js = [
            "admin/js/core.js",
            "admin/js/SelectBox.js",
            "admin/js/SelectFilter2.js",
            "lib/filteredselectmultiple.js",
        ]


class UserEditForm(UserChangeForm):
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.exclude(name__startswith='Can').order_by("name"), label="Permissions",
        widget=FilteredSelectMultiplePermissions("permissions", is_stacked=False),
        required=False)

    structures = forms.ModelMultipleChoiceField(
        queryset=Structure.objects.all().order_by("nom"), label="Structures",
        widget=RelatedFieldWidgetWrapper(
            FilteredSelectMultiple("structures", is_stacked=False),
            rel=Utilisateur._meta.get_field("structures").remote_field, admin_site=admin.site, can_add_related=False,
        ),
        required=False)

    class Meta:
        model = Utilisateur
        exclude = []


# --------------------------- Utilisateurs ----------------------------

class UtilisateurAdmin(UserAdmin):
    form = UserEditForm

    # Ajoute la colonne is_active dans la liste des utilisateurs
    list_display = UserAdmin.list_display + ('is_active',)

    # Affichage des champs
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'email')}),
        ('Activation du compte', {'fields': ('is_active',)}),
        ('Permissions accordées', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Structures accessibles', {'fields': ('structures',), 'description': "Sélectionnez les structures accessibles par cet utilisateur."}),
        ('Options', {'fields': ('adresse_exp', 'signature')}),
        ('Dates importantes', {'fields': ('last_login', 'date_joined')})
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(categorie="utilisateur")


class Utilisateur_Utilisateur(Utilisateur):
    class Meta:
        proxy = True
        verbose_name = "Utilisateur"

admin.site.register(Utilisateur_Utilisateur, UtilisateurAdmin)


# --------------------------- Familles ----------------------------

class FamilleAdmin(UserAdmin):
    form = UserEditForm

    # Affiche uniquement les colonnes suivantes dans la liste
    list_display = ('username', 'email', 'is_active')

    # Affiche uniquement les filtres suivants
    list_filter = ('is_active',)

    # Affiche uniquement les champs suivants
    fieldsets = (
        (None, {'fields': ('username', 'password', 'email')}),
        ('Permissions', {'fields': ('is_active', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'date_joined')})
    )

    def get_queryset(self, request):
        """ Affiche uniquement les utilisateurs de type famille """
        qs = super().get_queryset(request)
        return qs.filter(categorie="famille")

    def has_add_permission(self, request):
        """ Empêche l'ajout d'un utilisateur famille """
        return False

    def has_delete_permission(self, request, obj=None):
        """ Empêche la suppression d'un utilisateur famille """
        return False


class Utilisateur_Famille(Utilisateur):
    class Meta:
        proxy = True
        verbose_name = "Famille"


# admin.site.register(Utilisateur_Famille, FamilleAdmin)
