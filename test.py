import asyncio
from langchain_postgres import PGVectorStore

async def main():
    vector_store = await PGVectorStore.create(
        engine=engine,
        table_name="hc_ai_table",
        schema_name="hc_ai_schema",
        embedding_service=embedding,
    )

if __name__ == "__main__":
    asyncio.run(main())
    await vector_store.close()