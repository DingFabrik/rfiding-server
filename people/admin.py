from django.contrib import admin

from .models import Person, Qualification, Instructor


class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "email")
    search_fields = ("name", "email")


class QualificationAdmin(admin.ModelAdmin):
    pass


class InstructorAdmin(admin.ModelAdmin):
    pass


admin.site.register(Person, PersonAdmin)
admin.site.register(Qualification, QualificationAdmin)
admin.site.register(Instructor, InstructorAdmin)
