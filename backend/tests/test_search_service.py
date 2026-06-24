from app.models.schemas import SearchRequest
from app.services.container import search_service


def test_search_inventory_api():
    response = search_service.search(SearchRequest(query="即时库存查询接口", top_k=3))
    assert response.candidates
    assert any("库存" in item.name or "inv" in item.url.lower() for item in response.candidates)
