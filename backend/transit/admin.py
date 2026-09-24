import datetime
from django import forms
from django.contrib import admin
from .models import Evaluation, Simulation, Stop, Route, RouteStop, SourceDocument

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



@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "source", "lat", "lon")
    list_filter = ("source",)
    search_fields = ("id", "name")


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 0
    raw_id_fields = ("stop",)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "source", "simulated", "routable")
    list_filter = ("source", "simulated", "routable")
    search_fields = ("code", "name")
    inlines = (RouteStopInline,)


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ("provider", "kind", "status", "imported_at", "url")
    list_filter = ("provider", "kind", "status")
    search_fields = ("url", "content")
    readonly_fields = ("imported_at",)


from .models import GeolocationRun, StopEstimate

@admin.register(GeolocationRun)
class GeolocationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "algorithm", "source_hash")
    readonly_fields = ("created_at", "algorithm", "source_hash", "summary")

@admin.register(StopEstimate)
class StopEstimateAdmin(admin.ModelAdmin):
    list_display = ("stop", "route", "position", "status", "lat", "lon", "run")
    list_filter = ("status", "run")
    search_fields = ("stop__name", "route__code")
    readonly_fields = ("route", "stop", "position", "run", "status", "lat", "lon", "evidence")
