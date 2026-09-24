import datetime
from django import forms
from django.contrib import admin
from .models import Evaluation, Simulation

admin.site.site_header = "Meu Ponto · Administração"
admin.site.site_title = "Administração Meu Ponto"
admin.site.index_title = "Operação e avaliação"
admin.site.site_url = "/"


class SimulationForm(forms.ModelForm):
    simulated_time = forms.TimeField(
        label="Horário simulado",
        widget=forms.TimeInput(format="%H:%M:%S", attrs={"type": "time", "step": 1}),
    )

    class Meta:
        model = Simulation
        fields = ("enabled", "running", "simulated_time", "speed")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        seconds = self.instance.current_seconds() if self.instance.pk else 28800
        self.fields["simulated_time"].initial = datetime.time(
            seconds // 3600, (seconds % 3600) // 60, seconds % 60
        )

    def save(self, commit=True):
        value = self.cleaned_data["simulated_time"]
        self.instance.seconds = value.hour * 3600 + value.minute * 60 + value.second
        return super().save(commit=commit)


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):
    form = SimulationForm
    list_display = ("__str__", "enabled", "running", "speed")

    def has_add_permission(self, request):
        return not Simulation.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "scenario")
    readonly_fields = ("created_at",)
    search_fields = ("notes", "scenario")
