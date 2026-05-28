from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('betting', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bet',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='direccion IP'),
        ),
    ]
