from django.db import migrations


def update_prices(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    Plan.objects.filter(name='free').update(price_monthly=49)
    Plan.objects.filter(name='pro').update(price_monthly=129)
    Plan.objects.filter(name='business').update(price_monthly=269)


def revert_prices(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    Plan.objects.filter(name='free').update(price_monthly=0)
    Plan.objects.filter(name='pro').update(price_monthly=150)
    Plan.objects.filter(name='business').update(price_monthly=2999)


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(update_prices, revert_prices),
    ]