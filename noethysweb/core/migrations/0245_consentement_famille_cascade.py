# Les consentements d'une famille sont supprimés avec elle (auparavant PROTECT :
# une famille ayant donné un consentement sur le portail ne pouvait plus être supprimée).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0244_permissions_fiche_collaborateur"),
    ]

    operations = [
        migrations.AlterField(
            model_name="consentement",
            name="famille",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="core.famille",
                verbose_name="Famille",
            ),
        ),
    ]
