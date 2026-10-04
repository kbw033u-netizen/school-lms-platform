from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0003_alter_payment_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolclass",
            name="lesson_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]