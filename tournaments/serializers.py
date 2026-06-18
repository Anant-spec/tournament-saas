from rest_framework import serializers
from .models import Tournament, Match

class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'slug', 'game_title',
            'format_type', 'status', 'max_teams',
            'entry_fee', 'prize_pool', 'start_date',
            'registration_open', 'created_at',
        ]
        read_only_fields = ['id', 'slug', 'status', 'created_at']


class MatchSerializer(serializers.ModelSerializer):
    team1_name = serializers.CharField(source='team1.name', read_only=True)
    team2_name = serializers.CharField(source='team2.name', read_only=True)
    winner_name = serializers.CharField(source='winner.name', read_only=True)

    class Meta:
        model = Match
        fields = [
            'id', 'round_number', 'match_number',
            'team1', 'team1_name',
            'team2', 'team2_name',
            'winner', 'winner_name',
            'status', 'next_match',
        ]
        read_only_fields = ['id', 'round_number', 'match_number', 'next_match']