from rest_framework.routers import DefaultRouter

from .views import EquivalencyQueryViewSet

router = DefaultRouter()
router.register("equivalency-queries", EquivalencyQueryViewSet, basename="equivalency-query")

urlpatterns = router.urls
