"""
Management command to create sample test data for TeamSync.
Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from teams.models import Team, Channel, Membership
from chat.models import ChatMessage


class Command(BaseCommand):
    help = 'Create sample test data for TeamSync'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...\n')

        # Create users
        users = []
        user_data = [
            ('alice', 'alice@test.com', 'Alice', 'Johnson'),
            ('bob', 'bob@test.com', 'Bob', 'Smith'),
            ('charlie', 'charlie@test.com', 'Charlie', 'Brown'),
            ('diana', 'diana@test.com', 'Diana', 'Prince'),
        ]

        for uname, email, fname, lname in user_data:
            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': uname,
                    'first_name': fname,
                    'last_name': lname,
                    'is_verified': True,
                }
            )
            if created:
                user.set_password('test1234')
                user.save()
                self.stdout.write(f'  Created user: {email} (password: test1234)')
            users.append(user)

        alice, bob, charlie, diana = users

        # Create teams
        team1, _ = Team.objects.get_or_create(
            name='Engineering',
            defaults={'description': 'Software engineering team', 'created_by': alice}
        )
        team2, _ = Team.objects.get_or_create(
            name='Marketing',
            defaults={'description': 'Marketing and growth team', 'created_by': bob}
        )

        # Create channels
        for team in [team1, team2]:
            Channel.objects.get_or_create(team=team, name='General', defaults={'is_default': True})
            Channel.objects.get_or_create(team=team, name='Random')

        Channel.objects.get_or_create(team=team1, name='Code Reviews')
        Channel.objects.get_or_create(team=team2, name='Campaigns')

        # Add memberships
        for user in users:
            Membership.objects.get_or_create(
                user=user, team=team1,
                defaults={'role': 'admin' if user == alice else 'member'}
            )
        for user in [bob, charlie, diana]:
            Membership.objects.get_or_create(
                user=user, team=team2,
                defaults={'role': 'admin' if user == bob else 'member'}
            )

        # Create sample messages
        general = Channel.objects.get(team=team1, name='General')
        msgs = [
            (alice, 'Hey team! Welcome to the Engineering channel 🚀'),
            (bob, 'Thanks Alice! Excited to be here.'),
            (charlie, 'Let\'s build something amazing! 💪'),
        ]
        for sender, text in msgs:
            ChatMessage.objects.get_or_create(
                sender=sender, channel=general, message=text
            )

        # Create 1:1 messages
        dm_msgs = [
            (alice, bob, 'Hey Bob, how\'s the new feature coming along?'),
            (bob, alice, 'Going great! Should be done by EOD.'),
            (alice, bob, 'Awesome, let me know if you need any help!'),
        ]
        for sender, receiver, text in dm_msgs:
            ChatMessage.objects.get_or_create(
                sender=sender, receiver=receiver, message=text
            )

        self.stdout.write(self.style.SUCCESS(
            '\nSample data created successfully!\n'
            '\nTest Accounts:\n'
            '  alice@test.com / test1234\n'
            '  bob@test.com / test1234\n'
            '  charlie@test.com / test1234\n'
            '  diana@test.com / test1234\n'
        ))
