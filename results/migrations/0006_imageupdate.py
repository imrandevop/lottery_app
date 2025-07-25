# Generated by Django 5.2.1 on 2025-06-20 07:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("results", "0005_alter_lotteryresult_is_bumper"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImageUpdate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "update_image1",
                    models.URLField(
                        help_text="URL for the first update image",
                        max_length=500,
                        verbose_name="Update Image 1 URL",
                    ),
                ),
                (
                    "update_image2",
                    models.URLField(
                        help_text="URL for the second update image",
                        max_length=500,
                        verbose_name="Update Image 2 URL",
                    ),
                ),
                (
                    "update_image3",
                    models.URLField(
                        help_text="URL for the third update image",
                        max_length=500,
                        verbose_name="Update Image 3 URL",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Image Update",
                "verbose_name_plural": "Image Updates",
            },
        ),
    ]
