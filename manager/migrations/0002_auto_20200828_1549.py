# Generated by Django 3.1 on 2020-08-28 07:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order_detail',
            name='ingd_cost',
            field=models.FloatField(default=0, verbose_name='其他成本'),
        ),
    ]
