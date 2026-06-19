from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0004_tournament_entry_fee_tournament_max_teams_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='scheduled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
