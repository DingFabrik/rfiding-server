from django.db import migrations, models


def dedupe_qualifications(apps, schema_editor):
    Qualification = apps.get_model("people", "Qualification")
    seen_pairs = set()
    for qualification in Qualification.objects.order_by("person_id", "machine_id", "-created"):
        key = (qualification.person_id, qualification.machine_id)
        if key in seen_pairs:
            qualification.delete()
        else:
            seen_pairs.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ("people", "0021_person_detail_key_person_detail_key_expires_at"),
    ]

    operations = [
        migrations.RunPython(dedupe_qualifications, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="qualification",
            constraint=models.UniqueConstraint(
                fields=["person", "machine"], name="unique_qualification_person_machine"
            ),
        ),
    ]
