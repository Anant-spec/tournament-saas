from rest_framework.routers import DefaultRouter
from .api_views import TournamentViewSet, MatchViewSet

router = DefaultRouter()
router.register(r'tournaments', TournamentViewSet, basename='api-tournament')
router.register(r'matches', MatchViewSet, basename='api-match')

urlpatterns = router.urls