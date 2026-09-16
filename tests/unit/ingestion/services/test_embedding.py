from ingestion.chunker.models import CodeChunk
from ingestion.embeddings.base import EmbeddingProvider
from ingestion.parser.languages.base import SymbolType
from ingestion.services import EmbeddingService


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic embedding provider for unit tests."""

    @property
    def model_name(self) -> str:
        return "fake-model"

    @property
    def dimension(self) -> int:
        return 3

    async def embed(self, text: str) -> list[float]:
        return [1.0, 2.0, 3.0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 2.0, 3.0] for _ in texts]


def make_chunk(content: str = "def add(a, b):\n    return a + b") -> CodeChunk:
    return CodeChunk(
        file_path="src/math.py",
        content=content,
        symbol_name="add",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=2,
    )


async def test_embed_chunk() -> None:
    provider = FakeEmbeddingProvider()
    service = EmbeddingService(provider)

    embedding = await service.embed_chunk(make_chunk())

    assert embedding == [1.0, 2.0, 3.0]


async def test_embed_chunks() -> None:
    provider = FakeEmbeddingProvider()
    service = EmbeddingService(provider)

    chunks = [
        make_chunk("def add(a, b):\n    return a + b"),
        make_chunk("def subtract(a, b):\n    return a - b"),
    ]

    embeddings = await service.embed_chunks(chunks)

    assert embeddings == [
        [1.0, 2.0, 3.0],
        [1.0, 2.0, 3.0],
    ]


async def test_embed_chunks_empty() -> None:
    provider = FakeEmbeddingProvider()
    service = EmbeddingService(provider)

    embeddings = await service.embed_chunks([])

    assert embeddings == []
