# Generated by Django 2.2.10 on 2020-04-01 19:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('droplet', '0002_droplet_owner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='droplet',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL),
        ),
    ]