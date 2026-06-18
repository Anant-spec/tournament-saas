import math
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Tournament, Match
from .serializers import TournamentSerializer, MatchSerializer
from registrations.models import Team


class TournamentViewSet(viewsets.ModelViewSet):
    serializer_class = TournamentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Tournament.objects.filter(
            organization__owner=self.request.user
        ).select_related('organization', 'champion')

    @action(detail=True, methods=['get'])
    def matches(self, request, pk=None):
        tournament = self.get_object()
        matches = tournament.matches.order_by('round_number', 'match_number')
        serializer = MatchSerializer(matches, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def generate_bracket(self, request, pk=None):
        tournament = Tournament.objects.select_for_update().get(
            pk=pk, organization__owner=request.user
        )

        if tournament.format_type != 'single_elimination':
            return Response(
                {'error': 'Only single elimination supported.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if tournament.matches.exists():
            return Response(
                {'error': 'Bracket already generated.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        teams = [
            r.team for r in tournament.registrations
            .filter(status='approved')
            .select_related('team')
            .order_by('created_at', 'id')
        ]

        if len(teams) < 2:
            return Response(
                {'error': 'Need at least 2 approved teams.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        total_rounds = math.ceil(math.log2(len(teams)))
        bracket_size = 2 ** total_rounds

        all_matches = Match.objects.bulk_create([
            Match(tournament=tournament, round_number=r, match_number=m)
            for r in range(1, total_rounds + 1)
            for m in range(1, (bracket_size // (2 ** r)) + 1)
        ])

        round_map = {}
        for match in all_matches:
            round_map.setdefault(match.round_number, []).append(match)
        for r in round_map:
            round_map[r].sort(key=lambda m: m.match_number)

        to_update = []
        for r in range(1, total_rounds):
            for i, match in enumerate(round_map[r]):
                match.next_match = round_map[r + 1][i // 2]
                to_update.append(match)
        Match.objects.bulk_update(to_update, ['next_match'])

        slots = teams + [None] * (bracket_size - len(teams))
        first_round = round_map[1]
        for i, match in enumerate(first_round):
            match.team1 = slots[i * 2]
            match.team2 = slots[i * 2 + 1]
        Match.objects.bulk_update(first_round, ['team1', 'team2'])

        tournament.status = 'published'
        tournament.save(update_fields=['status'])

        return Response({'message': 'Bracket generated.'}, status=status.HTTP_201_CREATED)


class MatchViewSet(viewsets.ModelViewSet):
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'head', 'options']  # read-only; results go via custom action

    def get_queryset(self):
        return Match.objects.filter(
            tournament__organization__owner=self.request.user
        ).select_related('team1', 'team2', 'winner')

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def result(self, request, pk=None):
        match = Match.objects.select_for_update().select_related(
            'tournament', 'next_match', 'team1', 'team2'
        ).get(pk=pk, tournament__organization__owner=request.user)

        if match.status == 'completed':
            return Response({'error': 'Result already reported.'}, status=status.HTTP_400_BAD_REQUEST)

        winner_id = request.data.get('winner')
        if str(match.team1_id) == winner_id:
            winner = match.team1
        elif str(match.team2_id) == winner_id:
            winner = match.team2
        else:
            return Response({'error': 'Invalid winner.'}, status=status.HTTP_400_BAD_REQUEST)

        match.winner = winner
        match.status = 'completed'
        match.save(update_fields=['winner', 'status'])

        if match.next_match:
            next_match = Match.objects.select_for_update().get(pk=match.next_match.pk)
            if next_match.team1 is None:
                next_match.team1 = winner
                next_match.save(update_fields=['team1'])
            else:
                next_match.team2 = winner
                next_match.save(update_fields=['team2'])
            match.tournament.status = 'ongoing'
            match.tournament.save(update_fields=['status'])
        else:
            match.tournament.status = 'completed'
            match.tournament.champion = winner
            match.tournament.save(update_fields=['status', 'champion'])

        return Response({'message': 'Result recorded.'}, status=status.HTTP_200_OK)