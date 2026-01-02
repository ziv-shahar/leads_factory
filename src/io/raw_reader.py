"""Raw file reader with local filesystem support (S3-ready interface)."""
import os
from pathlib import Path
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
import json


class RawFileReader:
    """Read raw files from local filesystem (can be swapped to S3 later)."""

    def __init__(self, bucket_path: str):
        """
        Initialize reader.

        Args:
            bucket_path: Path to local bucket directory (or S3 bucket name in future)
        """
        self.bucket_path = Path(bucket_path)

    def list_files(self, pattern: str = "*") -> List[str]:
        """
        List files in bucket matching pattern.

        Args:
            pattern: Glob pattern (default: all files)

        Returns:
            List of file paths
        """
        if not self.bucket_path.exists():
            return []

        files = []
        for path in self.bucket_path.glob(pattern):
            if path.is_file():
                files.append(str(path))

        return sorted(files)

    def read_file(self, file_path: str) -> Tuple[str, str]:
        """
        Read and parse file content.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (content, file_type)
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine file type
        suffix = path.suffix.lower()

        # Read content
        if suffix in ['.html', '.htm']:
            return self._read_html(path), 'html'
        elif suffix == '.json':
            return self._read_json(path), 'json'
        elif suffix in ['.txt', '.text']:
            return self._read_text(path), 'text'
        else:
            # Fallback to text
            return self._read_text(path), 'text'

    def _read_html(self, path: Path) -> str:
        """Read and extract text from HTML."""
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Parse HTML and extract text
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator='\n')

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    def _read_json(self, path: Path) -> str:
        """Read JSON and convert to readable format."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Pretty print JSON for LLM readability
        return json.dumps(data, indent=2)

    def _read_text(self, path: Path) -> str:
        """Read plain text file."""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def get_relative_path(self, file_path: str) -> str:
        """Get path relative to bucket root."""
        path = Path(file_path)
        try:
            return str(path.relative_to(self.bucket_path))
        except ValueError:
            return str(path)
