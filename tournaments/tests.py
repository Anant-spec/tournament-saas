import math
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from organizations.models import Organization
from registrations.models import Team, Registration
from .models import Tournament, Match

User = get_user_model()


def create_user(username="testuser", password="pass1234"):
    return User.objects.create_user(username=username, password=password)


def create_org(owner):
    return Organization.objects.create(name="Test Org", owner=owner)


def create_tournament(org, name="Test Tournament", n_teams=4):
    t = Tournament.objects.create(
        organization=org,
        name=name,
        slug=name.lower().replace(" ", "-"),
        game_title="Valorant",
        format_type="single_elimination",
        status="draft",
    )
    teams = []
    for i in range(n_teams):
        team = Team.objects.create(
            tournament=t,
            name=f"Team {i + 1}",
            captain_name=f"Captain {i + 1}",
            captain_email=f"cap{i + 1}@test.com",
        )
        Registration.objects.create(tournament=t, team=team, status="approved")
        teams.append(team)
    return t, teams


class BracketGenerationTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.org = create_org(self.user)
        self.client = Client()
        self.client.login(username="testuser", password="pass1234")

    def _generate(self, tournament):
        url = reverse("generate_bracket", kwargs={"pk": tournament.pk})
        return self.client.post(url)

    def test_4_teams_creates_correct_match_count(self):
        """4 teams → 2 Round 1 matches + 1 final = 3 matches total."""
        t, _ = create_tournament(self.org, n_teams=4)
        self._generate(t)
        self.assertEqual(t.matches.count(), 3)

    def test_2_teams_creates_one_match(self):
        """2 teams → 1 match, no byes."""
        t, _ = create_tournament(self.org, n_teams=2)
        self._generate(t)
        self.assertEqual(t.matches.count(), 1)

    def test_3_teams_creates_byes(self):
        """3 teams → bracket_size=4, 1 bye. Round 1 has 1 match, Round 2 has 2 matches."""
        t, _ = create_tournament(self.org, n_teams=3)
        self._generate(t)
        r1 = t.matches.filter(round_number=1).count()
        r2 = t.matches.filter(round_number=2).count()
        self.assertEqual(r1, 1)
        self.assertEqual(r2, 2)

    def test_5_teams_bracket_size_is_8(self):
        """5 teams → bracket_size=8, 3 byes."""
        t, _ = create_tournament(self.org, n_teams=5)
        self._generate(t)
        total = t.matches.count()
        # Total matches = bracket_size - 1 = 7
        self.assertEqual(total, 7)

    def test_next_match_wiring_is_complete(self):
        """All non-final matches must have a next_match pointer."""
        t, _ = create_tournament(self.org, n_teams=4)
        self._generate(t)
        max_round = t.matches.order_by("-round_number").first().round_number
        non_final = t.matches.exclude(round_number=max_round)
        for m in non_final:
            self.assertIsNotNone(m.next_match, f"Match R{m.round_number}M{m.match_number} missing next_match")

    def test_final_match_has_no_next_match(self):
        """The final match must NOT have a next_match pointer."""
        t, _ = create_tournament(self.org, n_teams=4)
        self._generate(t)
        max_round = t.matches.order_by("-round_number").first().round_number
        final = t.matches.filter(round_number=max_round).first()
        self.assertIsNone(final.next_match)

    def test_tournament_status_becomes_published(self):
        t, _ = create_tournament(self.org, n_teams=4)
        self._generate(t)
        t.refresh_from_db()
        self.assertEqual(t.status, "published")

    def test_cannot_generate_bracket_twice(self):
        t, _ = create_tournament(self.org, n_teams=4)
        self._generate(t)
        self._generate(t)  # second call
        # Match count must not double
        self.assertEqual(t.matches.count(), 3)

    def test_less_than_2_teams_blocked(self):
        t, _ = create_tournament(self.org, n_teams=1)
        self._generate(t)
        self.assertEqual(t.matches.count(), 0)


class MatchReportTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.org = create_org(self.user)
        self.client = Client()
        self.client.login(username="testuser", password="pass1234")

    def _generate(self, tournament):
        url = reverse("generate_bracket", kwargs={"pk": tournament.pk})
        self.client.post(url)

    def _report(self, match, winner):
        url = reverse("report_match_result", kwargs={"match_id": match.pk})
        return self.client.post(url, {"winner": str(winner.pk)})

    def test_reporting_winner_marks_match_completed(self):
        t, teams = create_tournament(self.org, n_teams=2)
        self._generate(t)
        match = t.matches.first()
        self._report(match, match.team1)
        match.refresh_from_db()
        self.assertEqual(match.status, "completed")
        self.assertEqual(match.winner, match.team1)

    def test_winner_advances_to_next_match(self):
        """In a 4-team bracket, Round 1 winner must appear in Round 2 match."""
        t, teams = create_tournament(self.org, n_teams=4)
        self._generate(t)
        r1_match = t.matches.filter(round_number=1).first()
        winner = r1_match.team1
        self._report(r1_match, winner)
        next_m = Match.objects.get(pk=r1_match.next_match.pk)
        self.assertIn(winner, [next_m.team1, next_m.team2])

    def test_completing_final_sets_champion(self):
        t, teams = create_tournament(self.org, n_teams=2)
        self._generate(t)
        final = t.matches.first()
        self._report(final, final.team1)
        t.refresh_from_db()
        self.assertEqual(t.status, "completed")
        self.assertEqual(t.champion, final.team1)

    def test_cannot_report_already_completed_match(self):
        t, teams = create_tournament(self.org, n_teams=2)
        self._generate(t)
        match = t.matches.first()
        self._report(match, match.team1)
        # Report again — should redirect with error, not crash
        response = self._report(match, match.team2)
        self.assertEqual(response.status_code, 302)
        match.refresh_from_db()
        self.assertEqual(match.winner, match.team1)  # unchanged

    def test_invalid_winner_id_rejected(self):
        t, teams = create_tournament(self.org, n_teams=2)
        self._generate(t)
        match = t.matches.first()
        url = reverse("report_match_result", kwargs={"match_id": match.pk})
        response = self.client.post(url, {"winner": "invalid-uuid"})
        self.assertEqual(response.status_code, 302)
        match.refresh_from_db()
        self.assertEqual(match.status, "pending")  # unchanged
