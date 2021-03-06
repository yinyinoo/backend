# Generated by Django 3.1 on 2020-08-29 07:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0003_order_detail_start_time'),
    ]

    operations = [
        migrations.CreateModel(
            name='order_choice_log',
            fields=[
                ('choice_id', models.AutoField(primary_key=True, serialize=False)),
                ('add_order_type', models.IntegerField(default=0, verbose_name='加单算法选择')),
                ('nudge_order_type', models.IntegerField(default=0, verbose_name='催单算法选择')),
                ('create_time', models.DateTimeField(auto_now=True, verbose_name='使用算法的时间')),
            ],
        ),
    ]
