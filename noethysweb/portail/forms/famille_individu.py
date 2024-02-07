from django import forms
from django.forms import ModelForm
from core.models import Individu
from django.shortcuts import render

class IndividuForm(forms.ModelForm):
    class Meta:
        model = Individu
        fields = ['prenom', 'nom']

def contact(request):
    contact_form = IndividuForm()
    return render(request,'portail/famille_individu.html' ,{'contact_form': contact_form})