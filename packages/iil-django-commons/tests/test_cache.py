def test_cached_view_stores_response(rf):
    from django.http import HttpResponse

    from iil_commons.cache.decorators import cached_view

    call_count = 0

    @cached_view(ttl=60)
    def my_view(request):
        nonlocal call_count
        call_count += 1
        return HttpResponse(f"response-{call_count}")

    request = rf.get("/test/")
    r1 = my_view(request)
    r2 = my_view(request)

    assert r1.content == r2.content
    assert call_count == 1


def test_cached_method_stores_result():
    from iil_commons.cache.decorators import cached_method

    class MyService:
        call_count = 0

        @cached_method(ttl=60, key_prefix="test_service")
        def compute(self, x: int) -> int:
            self.call_count += 1
            return x * 2

    svc = MyService()
    assert svc.compute(5) == 10
    assert svc.compute(5) == 10
    assert svc.call_count == 1


def test_invalidate_pattern_locmem_warns(caplog):
    import logging

    from iil_commons.cache.invalidation import invalidate_pattern

    with caplog.at_level(logging.WARNING, logger="iil_commons.cache.invalidation"):
        count = invalidate_pattern("iil:view:*")

    assert count == 0
    assert "iter_keys" in caplog.text
