# Generated by Django 2.0 on 2019-08-13 08:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('xfzauth', '0002_auto_20190812_1716'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='is_stuff',
            new_name='is_staff',
        ),
    ]
