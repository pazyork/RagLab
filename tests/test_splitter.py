import pytest
from raglab.core.splitter import split_lines, split_by_char, split_by_recursive


class TestSplitter:
    def test_split_lines_empty_text(self):
        """Test split_lines with empty text returns empty list"""
        assert split_lines("") == []
        assert split_lines("   ") == []
        assert split_lines("\n\n\n") == []

    def test_split_lines_normal_text(self):
        """Test split_lines correctly splits by line and filters empty lines"""
        text = """line1
line2

line3
   line4
"""
        assert split_lines(text) == ["line1", "line2", "line3", "line4"]

    def test_split_by_char_empty_text(self):
        """Test split_by_char with empty text returns empty list"""
        assert split_by_char("") == []
        assert split_by_char("   ") == []

    def test_split_by_char_short_text(self):
        """Test split_by_char with text shorter than chunk_size returns single element"""
        text = "short text"
        assert split_by_char(text, chunk_size=100) == [text]

    def test_split_by_char_exact_chunk_size(self):
        """Test split_by_char with text exactly chunk_size returns single element"""
        text = "a" * 512
        result = split_by_char(text, chunk_size=512)
        assert len(result) == 1
        assert len(result[0]) == 512

    def test_split_by_char_multiple_chunks_no_overlap(self):
        """Test split_by_char creates multiple chunks with no overlap"""
        text = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" * 10  # 620 chars
        result = split_by_char(text, chunk_size=100, overlap=0)

        # Verify chunk count and sizes
        assert len(result) == 7  # 100*6 + 20 = 620
        assert len(result[0]) == 100
        assert len(result[1]) == 100
        assert len(result[2]) == 100
        assert len(result[3]) == 100
        assert len(result[4]) == 100
        assert len(result[5]) == 100
        assert len(result[6]) == 20

        # Verify no overlap by checking content concatenation
        combined = "".join(result)
        assert combined == text  # All content should be preserved exactly with no duplication

        # Verify no overlap by checking boundary content
        assert result[0][-5:] == text[95:100]
        assert result[1][:5] == text[100:105]
        assert result[0][-5:] != result[1][:5]  # Different content at boundaries

    def test_split_by_char_with_overlap(self):
        """Test split_by_char correctly applies overlap between chunks"""
        text = "abcdefghijklmnopqrstuvwxyz" * 10  # 260 chars
        chunk_size = 100
        overlap = 20
        result = split_by_char(text, chunk_size=chunk_size, overlap=overlap)

        # Check overlap between chunks
        for i in range(len(result) - 1):
            # The end of current chunk should match the start of next chunk
            assert result[i][-overlap:] == result[i+1][:overlap]

        # Total length should be reasonable
        total_chars = sum(len(chunk) for chunk in result)
        assert total_chars >= len(text)
        assert total_chars <= len(text) + overlap * (len(result) - 1)

    def test_split_by_recursive_empty_text(self):
        """Test split_by_recursive with empty text returns empty list"""
        assert split_by_recursive("") == []
        assert split_by_recursive("   ") == []

    def test_split_by_recursive_short_text(self):
        """Test split_by_recursive with text shorter than chunk_size returns single element"""
        text = "short text that is less than chunk size"
        result = split_by_recursive(text, chunk_size=100, chunk_overlap=10)
        assert len(result) == 1
        assert result[0] == text

    def test_split_by_recursive_paragraph_priority(self):
        """Test split_by_recursive prioritizes splitting by paragraphs first"""
        text = """Paragraph 1: This is the first paragraph. It has multiple sentences. It is quite long but should be kept as a single chunk if possible.

Paragraph 2: This is the second paragraph. It is also quite long and should be kept as a separate chunk.

Paragraph 3: This is the third paragraph."""

        result = split_by_recursive(text, chunk_size=200, chunk_overlap=20)
        # Should split into 3 paragraphs if each is under 200 chars
        assert len(result) == 3
        assert "Paragraph 1" in result[0]
        assert "Paragraph 2" in result[1]
        assert "Paragraph 3" in result[2]
        # No overlap between paragraphs (overlap only applies to final char split)
        assert result[0][-20:] != result[1][:20]

    def test_split_by_recursive_long_paragraph_split_by_sentence(self):
        """Test split_by_recursive splits long paragraphs into sentences first"""
        # Create a long paragraph with multiple sentences
        text = "这是第一句话。这是第二句话，稍微长一点。这是第三句话，也很长，包含了很多内容。这是第四句话，用来测试句子级别的切分。这是第五句话，最后一句。"

        # Chunk size small enough to force splitting but large enough for single sentences
        result = split_by_recursive(text, chunk_size=30, chunk_overlap=5)

        # Should split into multiple chunks by sentences
        assert len(result) > 1
        # Each chunk should end with a sentence terminator or be the end of text
        for chunk in result[:-1]:
            assert chunk[-1] in ["。", ".", "！", "!", "？", "?"]

    def test_split_by_recursive_chinese_text_compatibility(self):
        """Test split_by_recursive works correctly with Chinese text"""
        text = """随着人工智能技术的快速发展，大语言模型在各个领域得到了广泛应用。
        检索增强生成（RAG）技术能够有效解决大模型 hallucination 问题，同时提供可追溯的知识来源。
        文本切块是 RAG 系统中的关键步骤，直接影响后续检索的准确性和生成质量。
        不同的切分策略适用于不同类型的文本数据，需要根据实际场景进行选择和调优。"""

        result = split_by_recursive(text, chunk_size=100, chunk_overlap=10)
        assert len(result) > 0
        # All chunks should be non-empty
        assert all(len(chunk.strip()) > 0 for chunk in result)
        # Total content should be preserved
        combined = "".join(result)
        # Check that key content is present
        assert "人工智能" in combined
        assert "检索增强生成" in combined
        assert "文本切块" in combined

    def test_split_by_recursive_mixed_language(self):
        """Test split_by_recursive works with mixed Chinese and English text"""
        text = """Python是一种非常流行的编程语言。It is widely used in data science and machine learning.
        它的语法简洁，易于学习。Many developers prefer Python for its rich ecosystem of libraries.
        RAG技术结合了检索和生成的优势。It provides more accurate and reliable outputs for knowledge-intensive tasks."""

        result = split_by_recursive(text, chunk_size=80, chunk_overlap=10)
        assert len(result) > 0
        # Verify mixed content is handled properly
        assert any("Python" in chunk for chunk in result)
        assert any("编程语言" in chunk for chunk in result)
        assert any("RAG技术" in chunk for chunk in result)

    def test_split_by_recursive_final_char_split_overlap(self):
        """Test that overlap is only applied when doing final character level split"""
        # Create a very long continuous text with no natural separators
        text = "a" * 1000
        chunk_size = 200
        chunk_overlap = 30

        result = split_by_recursive(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        # Should be split into char chunks with overlap
        assert len(result) > 1
        # Check overlap between chunks
        for i in range(len(result) - 1):
            assert result[i][-chunk_overlap:] == result[i+1][:chunk_overlap]
