from django.contrib import admin

from people.models import Person, Qualification

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    pass

@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    pass