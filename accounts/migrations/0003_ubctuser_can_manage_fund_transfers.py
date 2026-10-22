from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_ubctuser_can_approve_requests"),
    ]

    operations = [
        migrations.AddField(
            model_name="ubctuser",
            name="can_manage_fund_transfers",
            field=models.BooleanField(
                default=False,
                help_text="Can this user record fund transfers and complete approved requests?",
            ),
        ),
    ]
