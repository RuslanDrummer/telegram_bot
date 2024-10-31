import asyncio
from bot import create_db_pool, initialize_db

async def main():
    pool = await create_db_pool()
    await initialize_db(pool)
    await pool.close()

asyncio.run(main())
