from datetime import UTC, datetime

import pytest

from httpx import AsyncClient


class TestNewsAPI:
    endpoint = "news/list-news"

    @pytest.mark.asyncio
    async def test_get_news_empty(
        self,
        # service fixtures
        client: AsyncClient,
    ):
        response = await client.get(self.endpoint)

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_news_only_inactive(
        self,
        # service fixtures
        client: AsyncClient,
        # fixtures for test
        news_factory,
    ):
        await news_factory(is_active=False)

        response = await client.get(self.endpoint)

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_active_news_sorted(
        self,
        # service fixtures
        client: AsyncClient,
        # fixtures for test
        news_factory,
    ):
        # Дата и порядок создания намеренно не совпадают с порядком выдачи.
        low_priority = await news_factory(
            title="Свежая новость с низким приоритетом",
            text="Текст первой новости",
            priority=1,
            updated_at=datetime(2026, 1, 3, tzinfo=UTC),
        )
        high_priority_new = await news_factory(
            title="Важная новая новость",
            text="Текст второй новости",
            priority=5,
            updated_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
        high_priority_old = await news_factory(
            title="Важная старая новость",
            text="Текст третьей новости",
            priority=5,
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        await news_factory(
            is_active=False,
            priority=100,
            updated_at=datetime(2026, 1, 4, tzinfo=UTC),
        )

        # Список новостей доступен без авторизации.
        response = await client.get(self.endpoint)

        assert response.status_code == 200
        assert response.json() == [
            {
                "id": high_priority_new.id,
                "title": "Важная новая новость",
                "text": "Текст второй новости",
                "updated_at": "2026-01-02T00:00:00Z",
            },
            {
                "id": high_priority_old.id,
                "title": "Важная старая новость",
                "text": "Текст третьей новости",
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": low_priority.id,
                "title": "Свежая новость с низким приоритетом",
                "text": "Текст первой новости",
                "updated_at": "2026-01-03T00:00:00Z",
            },
        ]
