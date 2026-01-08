# Generated manually on 2026-01-08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("results", "0036_textupdate"),
    ]

    operations = [
        migrations.AddField(
            model_name="lotteryresult",
            name="alphabet_set",
            field=models.CharField(
                choices=[
                    ("set1", "Set-1 (A, B, C, D, E, F, G, H, J, K, L, M)"),
                    ("set2", "Set-2 (N, O, P, R, S, T, U, V, W, X, Y, Z)"),
                ],
                default="set1",
                help_text="Alphabet set for generating consolation prizes",
                max_length=10,
                verbose_name="Alphabet Set",
            ),
        ),
    ]
