from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0006_remove_schoolclass_zoom_meeting_id_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="schoolclass",
            old_name="google_calendar_event_id",
            new_name="google_meet_space_name",
        ),
    ]
