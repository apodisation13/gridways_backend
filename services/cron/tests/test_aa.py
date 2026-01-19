import pytest


@pytest.mark.usefixtures("setup_database")
def test_aaaaa():
    print(999)
    print(999)
    assert True


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_bbbbb(db_pool):
    async with db_pool.acquire() as conn:
        u = await conn.fetch("select * from users")
        print(15, u)
    print(888)
    assert True


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_ccccc(db_pool):
    async with db_pool.acquire() as conn:
        u = await conn.fetch("select * from users")
        print(25, u)
    print(777)
    assert True
