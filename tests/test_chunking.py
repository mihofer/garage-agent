from mcp_server.knowledge import chunk_page


def test_short_text_single_chunk():
    text = "Tighten the M12 bolts to 120 Nm."
    assert chunk_page(text) == [text]


def test_paragraph_splitting():
    text = "\n\n".join(f"para {i} " + "x" * 300 for i in range(10))
    assert len(text) > 1200          # sanity: must exceed one chunk
    chunks = chunk_page(text)
    assert len(chunks) > 1
    joined = "\n".join(chunks)
    for i in range(10):
        assert f"para {i}" in joined


def test_no_content_lost():
    text = "\n\n".join("word " * 50 for _ in range(20))
    chunks = chunk_page(text)
    assert sum(len(c) for c in chunks) >= len(text.replace("\n", "")) - 40


def test_oversized_block_hard_split():
    wall = "A" * 5000
    chunks = chunk_page(wall)
    assert all(len(c) <= 1200 for c in chunks)
    assert "".join(chunks).count("A") == 5000


def test_empty_and_whitespace_only():
    assert chunk_page("") == []
    assert chunk_page("\n\n   \n") == []
